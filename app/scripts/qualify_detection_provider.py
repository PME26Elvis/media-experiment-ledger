from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
TOOLS_ROOT = REPO_ROOT / 'tools'
ENGINE_ROOT = APP_ROOT / 'engine'
for root in (TOOLS_ROOT, ENGINE_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import yolo_core  # type: ignore  # noqa: E402
from mel_engine.providers import (  # noqa: E402
    PROVIDER_MAP,
    create_session_options,
    prepare_runtime,
    provider_plan,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(root: Path, lock: dict[str, Any]) -> Path:
    path = root / 'yolox_tiny.onnx'
    request = urllib.request.Request(
        str(lock['download_url']),
        headers={'User-Agent': 'media-experiment-ledger-provider-qualification/1'},
    )
    with urllib.request.urlopen(request, timeout=240) as response, path.open('wb') as target:
        while chunk := response.read(4 * 1024 * 1024):
            target.write(chunk)
    actual = sha256(path)
    if path.stat().st_size != int(lock['expected_size_bytes']) or actual != str(lock['sha256']):
        raise RuntimeError(
            f'pinned model verification failed: bytes={path.stat().st_size} sha256={actual}',
        )
    return path


def test_image(width: int, height: int) -> Image.Image:
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = ((x * 13 + y * 3) % 256, (x * 5 + y * 11) % 256, (x * 7 + y * 17) % 256)
    draw = ImageDraw.Draw(image)
    draw.rectangle((32, 40, 210, 280), outline='white', width=6)
    draw.ellipse((230, 90, 390, 250), outline='black', width=5)
    return image


def profile_provider_counts(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    counts: dict[str, int] = {}
    for event in payload:
        provider = (event.get('args') or {}).get('provider')
        if isinstance(provider, str) and provider:
            counts[provider] = counts.get(provider, 0) + 1
    return dict(sorted(counts.items()))


def infer(
    ort: Any,
    model_path: Path,
    tensor: np.ndarray,
    provider_key: str,
    root: Path,
    *,
    device_id: int,
) -> tuple[np.ndarray, float, list[str], dict[str, int], dict[str, Any]]:
    requested_provider = PROVIDER_MAP[provider_key]
    prepare_runtime(ort, requested_provider)
    plan = provider_plan(
        provider_key,
        list(ort.get_available_providers()),
        allow_cpu_fallback=True,
        model_path=model_path,
        device_id=device_id,
    )
    options = create_session_options(
        ort,
        primary_provider=str(plan['active_provider']),
        allow_cpu_fallback=True,
        profile_prefix=root / f'{provider_key}-profile',
    )
    session = ort.InferenceSession(
        str(model_path),
        sess_options=options,
        providers=plan['providers'],
    )
    input_name = session.get_inputs()[0].name
    output_names = [item.name for item in session.get_outputs()]
    started = time.perf_counter()
    outputs = session.run(output_names, {input_name: tensor})
    elapsed_ms = (time.perf_counter() - started) * 1000
    profile_path = Path(session.end_profiling())
    serializable_plan = {
        key: value
        for key, value in plan.items()
        if key != 'providers'
    }
    return (
        np.asarray(outputs[0]),
        elapsed_ms,
        session.get_providers(),
        profile_provider_counts(profile_path),
        serializable_plan,
    )


def comparison(cpu: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    if cpu.shape != target.shape:
        return {
            'same_shape': False,
            'cpu_shape': list(cpu.shape),
            'target_shape': list(target.shape),
            'finite': False,
            'relative_rmse': None,
            'max_absolute_difference': None,
            'passed': False,
        }
    delta = target.astype(np.float64) - cpu.astype(np.float64)
    denominator = float(np.sqrt(np.mean(np.square(cpu.astype(np.float64))))) + 1e-12
    relative_rmse = float(np.sqrt(np.mean(np.square(delta))) / denominator)
    max_absolute = float(np.max(np.abs(delta)))
    finite = bool(np.isfinite(target).all())
    return {
        'same_shape': True,
        'cpu_shape': list(cpu.shape),
        'target_shape': list(target.shape),
        'finite': finite,
        'relative_rmse': relative_rmse,
        'max_absolute_difference': max_absolute,
        'relative_rmse_limit': 0.02,
        'max_absolute_difference_limit': 5.0,
        'passed': finite and relative_rmse <= 0.02 and max_absolute <= 5.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Qualify an ONNX Runtime execution provider against the CPU baseline.')
    parser.add_argument('--provider', choices=sorted(PROVIDER_MAP), required=True)
    parser.add_argument('--device-id', type=int, default=0)
    parser.add_argument('--required', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {
        'schema_version': 2,
        'requested_provider': args.provider,
        'provider': PROVIDER_MAP[args.provider],
        'device_id': args.device_id,
        'required': args.required,
        'platform': platform.system().lower(),
        'machine': platform.machine().lower(),
        'runner_name': os.environ.get('RUNNER_NAME'),
        'runner_environment': os.environ.get('RUNNER_ENVIRONMENT'),
        'passed': False,
    }
    try:
        import onnxruntime as ort

        provider = PROVIDER_MAP[args.provider]
        prepare_runtime(ort, provider)
        available = list(ort.get_available_providers())
        evidence.update({
            'runtime_version': ort.__version__,
            'runtime_device': ort.get_device(),
            'available_providers': available,
            'available': provider in available,
        })
        if provider not in available:
            evidence['status'] = 'unavailable'
            evidence['passed'] = not args.required
            return_code = 0 if evidence['passed'] else 1
        else:
            lock = json.loads((REPO_ROOT / 'object-detection' / 'model-lock.json').read_text(encoding='utf-8'))
            labels_path = REPO_ROOT / str(lock['labels_path'])
            with tempfile.TemporaryDirectory(prefix='mel-provider-qualification-') as directory:
                root = Path(directory)
                model_path = download_model(root, lock)
                yolo_core.verify_model_and_labels(model_path, lock, labels_path)
                prepared = yolo_core.prepare_image(
                    test_image(int(lock['input_width']), int(lock['input_height'])),
                    (int(lock['input_height']), int(lock['input_width'])),
                )
                cpu_output, cpu_ms, cpu_session_providers, cpu_profile, cpu_plan = infer(
                    ort,
                    model_path,
                    prepared.tensor,
                    'cpu',
                    root,
                    device_id=0,
                )
                target_output, target_ms, target_session_providers, target_profile, target_plan = infer(
                    ort,
                    model_path,
                    prepared.tensor,
                    args.provider,
                    root,
                    device_id=args.device_id,
                )
                comparison_result = comparison(cpu_output, target_output)
                assigned_nodes = int(target_profile.get(provider, 0))
                evidence.update({
                    'status': 'executed',
                    'model_sha256': sha256(model_path),
                    'input_shape': list(prepared.tensor.shape),
                    'cpu': {
                        'elapsed_ms': round(cpu_ms, 3),
                        'session_providers': cpu_session_providers,
                        'profile_provider_nodes': cpu_profile,
                        'provider_plan': cpu_plan,
                    },
                    'target': {
                        'elapsed_ms': round(target_ms, 3),
                        'session_providers': target_session_providers,
                        'profile_provider_nodes': target_profile,
                        'assigned_node_count': assigned_nodes,
                        'provider_plan': target_plan,
                    },
                    'comparison': comparison_result,
                })
                evidence['passed'] = assigned_nodes > 0 and comparison_result['passed']
                return_code = 0 if evidence['passed'] else 1
    except Exception as error:
        evidence['status'] = 'error'
        evidence['error'] = {
            'name': type(error).__name__,
            'message': str(error),
        }
        return_code = 1
    finally:
        output_path.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(evidence, indent=2))
    return return_code


if __name__ == '__main__':
    raise SystemExit(main())
