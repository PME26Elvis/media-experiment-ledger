from __future__ import annotations

import importlib.metadata
import platform
from pathlib import Path
from typing import Any


PROVIDER_MAP = {
    'cpu': 'CPUExecutionProvider',
    'cuda': 'CUDAExecutionProvider',
    'directml': 'DmlExecutionProvider',
    'coreml': 'CoreMLExecutionProvider',
}

_RUNTIME_DISTRIBUTIONS = (
    'onnxruntime',
    'onnxruntime-directml',
    'onnxruntime-gpu',
    'nvidia-cuda-runtime-cu12',
    'nvidia-cudnn-cu12',
)


def _distribution_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in _RUNTIME_DISTRIBUTIONS:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def provider_name(requested: str) -> str:
    key = requested.lower()
    if key not in PROVIDER_MAP:
        raise ValueError(f'Unsupported execution provider key: {requested!r}')
    return PROVIDER_MAP[key]


def prepare_runtime(ort: Any, provider: str) -> None:
    """Load optional vendor DLLs before a CUDA session when pip extras provide them."""
    if provider != 'CUDAExecutionProvider' or not hasattr(ort, 'preload_dlls'):
        return
    distributions = _distribution_versions()
    if 'nvidia-cuda-runtime-cu12' not in distributions and 'nvidia-cudnn-cu12' not in distributions:
        return
    ort.preload_dlls(directory='')


def provider_options(
    provider: str,
    *,
    model_path: Path | None = None,
    device_id: int = 0,
) -> dict[str, str]:
    if device_id < 0:
        raise ValueError('device_id must be zero or greater')
    if provider == 'CUDAExecutionProvider':
        return {
            'device_id': str(device_id),
            'arena_extend_strategy': 'kSameAsRequested',
            'do_copy_in_default_stream': '1',
        }
    if provider == 'CoreMLExecutionProvider':
        options = {
            'ModelFormat': 'MLProgram',
            'MLComputeUnits': 'ALL',
            'RequireStaticInputShapes': '0',
            'EnableOnSubgraphs': '0',
        }
        if model_path is not None:
            cache = model_path.parent / '.mel-provider-cache' / 'coreml'
            cache.mkdir(parents=True, exist_ok=True)
            options['ModelCacheDirectory'] = str(cache)
        return options
    return {}


def provider_plan(
    requested: str,
    available: list[str],
    *,
    allow_cpu_fallback: bool,
    model_path: Path | None = None,
    device_id: int = 0,
) -> dict[str, Any]:
    requested_key = requested.lower()
    desired = provider_name(requested_key)
    active = desired
    unavailable_fallback = False

    if desired not in available:
        if desired == 'CPUExecutionProvider' or 'CPUExecutionProvider' not in available:
            raise RuntimeError(f'Requested provider {desired} is unavailable: {available}')
        if not allow_cpu_fallback:
            raise RuntimeError(
                f'Requested execution provider {requested_key!r} is unavailable. '
                'Choose an available provider or explicitly enable CPU fallback.',
            )
        active = 'CPUExecutionProvider'
        unavailable_fallback = True

    active_options = provider_options(active, model_path=model_path, device_id=device_id)
    entries: list[Any] = [(active, active_options)] if active_options else [active]
    names = [active]
    options = [active_options]

    if (
        active != 'CPUExecutionProvider'
        and allow_cpu_fallback
        and 'CPUExecutionProvider' in available
    ):
        entries.append('CPUExecutionProvider')
        names.append('CPUExecutionProvider')
        options.append({})

    return {
        'requested_key': requested_key,
        'requested_provider': desired,
        'active_provider': active,
        'providers': entries,
        'provider_names': names,
        'provider_options': options,
        'allow_cpu_fallback': allow_cpu_fallback,
        'provider_fallback': unavailable_fallback,
        'device_id': device_id,
    }


def create_session_options(
    ort: Any,
    *,
    primary_provider: str,
    allow_cpu_fallback: bool,
    profile_prefix: Path | None = None,
) -> Any:
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if profile_prefix is not None:
        options.enable_profiling = True
        options.profile_file_prefix = str(profile_prefix)
    if primary_provider == 'DmlExecutionProvider':
        options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    if primary_provider != 'CPUExecutionProvider' and not allow_cpu_fallback:
        options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
    return options


def provider_inventory() -> dict[str, Any]:
    try:
        import onnxruntime as ort
    except ImportError as error:
        raise RuntimeError('onnxruntime is required for provider inventory') from error

    available = list(ort.get_available_providers())
    support = {
        key: {
            'provider': provider,
            'available': provider in available,
        }
        for key, provider in PROVIDER_MAP.items()
    }
    return {
        'schema_version': 2,
        'runtime_version': ort.__version__,
        'runtime_device': ort.get_device(),
        'platform': platform.system().lower(),
        'machine': platform.machine().lower(),
        'available_providers': available,
        'provider_support': support,
        'distributions': _distribution_versions(),
    }
