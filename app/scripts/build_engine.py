from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
ENGINE_ROOT = APP_ROOT / 'engine'
DIST_ROOT = APP_ROOT / 'engine-bin'
BUILD_ROOT = APP_ROOT / '.engine-build'
EXECUTABLE_NAME = 'mel-engine.exe' if os.name == 'nt' else 'mel-engine'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    print('+', subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, check=True, text=True, **kwargs)


def build() -> Path:
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)

    data_separator = ';' if os.name == 'nt' else ':'
    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onedir',
        '--name',
        'mel-engine',
        '--distpath',
        str(DIST_ROOT),
        '--workpath',
        str(BUILD_ROOT / 'work'),
        '--specpath',
        str(BUILD_ROOT / 'spec'),
        '--paths',
        str(ENGINE_ROOT),
        '--paths',
        str(REPO_ROOT / 'tools'),
        '--hidden-import',
        'yolo_core',
        '--hidden-import',
        'nanodet_core',
        '--collect-all',
        'onnxruntime',
        '--collect-all',
        'imageio',
        '--collect-all',
        'imageio_ffmpeg',
        '--copy-metadata',
        'onnxruntime',
        '--copy-metadata',
        'httpx',
        '--add-data',
        f"{REPO_ROOT / 'object-detection' / 'coco-80.json'}{data_separator}mel_engine/data",
        str(ENGINE_ROOT / 'mel_engine_entry.py'),
    ]
    run(command, cwd=APP_ROOT)
    executable = DIST_ROOT / 'mel-engine' / EXECUTABLE_NAME
    if not executable.is_file():
        raise RuntimeError(f'PyInstaller did not create {executable}')
    return executable


def invoke(executable: Path, request: dict[str, Any]) -> dict[str, Any]:
    completed = run(
        [str(executable)],
        cwd=executable.parent,
        input=json.dumps(request) + '\n',
        capture_output=True,
        timeout=120,
    )
    events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    results = [event for event in events if event.get('type') == 'result']
    errors = [event for event in events if event.get('type') == 'error']
    if errors or not results:
        raise RuntimeError(
            f'Engine request failed. request={request!r} stdout={completed.stdout!r} stderr={completed.stderr!r}',
        )
    return results[-1].get('data', {})


def smoke(executable: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        inputs = root / 'inputs'
        output = root / 'project'
        inputs.mkdir()
        scan = invoke(executable, {
            'operation': 'scan',
            'job_id': 'engine-build-smoke',
            'image_path': str(inputs),
            'video_path': '',
            'output_path': str(output),
            'import_mode': 'reference',
        })
        if (
            scan.get('indexed_count') != 0
            or scan.get('error_count') != 0
            or not (output / 'media-index.json').is_file()
        ):
            raise RuntimeError(f'Engine scan smoke failed: {scan!r}')

        providers = invoke(executable, {
            'operation': 'providers',
            'job_id': 'engine-provider-smoke',
        })
        available = providers.get('available_providers')
        if not isinstance(available, list) or 'CPUExecutionProvider' not in available:
            raise RuntimeError(f'Packaged engine provider inventory is invalid: {providers!r}')
        if os.name == 'nt' and 'DmlExecutionProvider' not in available:
            raise RuntimeError(f'Windows engine is missing DirectML: {providers!r}')
        return providers


def installed_distribution_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ('onnxruntime', 'onnxruntime-directml', 'onnxruntime-gpu'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def write_manifest(executable: Path, providers: dict[str, Any]) -> None:
    files = []
    for path in sorted(executable.parent.rglob('*')):
        if path.is_file():
            files.append({
                'path': path.relative_to(executable.parent).as_posix(),
                'size_bytes': path.stat().st_size,
                'sha256': sha256(path),
            })
    manifest = {
        'schema_version': 2,
        'engine_version': '0.1.0',
        'python_version': platform.python_version(),
        'platform': platform.system().lower(),
        'machine': platform.machine().lower(),
        'entrypoint': executable.relative_to(APP_ROOT).as_posix(),
        'entrypoint_sha256': sha256(executable),
        'file_count': len(files),
        'total_bytes': sum(item['size_bytes'] for item in files),
        'provider_inventory': providers,
        'build_distributions': installed_distribution_versions(),
        'capabilities': [
            'scan',
            'image-atlas',
            'video-atlas',
            'agnes-image-automation',
            'agnes-video-automation',
            'yolox-detection',
            'nanodet-detection',
            'sample-download',
            'provider-inventory',
        ],
        'files': files,
    }
    manifest_path = executable.parent / 'engine-build-manifest.json'
    temporary = manifest_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temporary.replace(manifest_path)
    print(json.dumps({
        'engine': str(executable),
        'files': manifest['file_count'],
        'bytes': manifest['total_bytes'],
        'sha256': manifest['entrypoint_sha256'],
        'providers': providers.get('available_providers'),
    }, indent=2))


def main() -> int:
    executable = build()
    providers = smoke(executable)
    write_manifest(executable, providers)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
