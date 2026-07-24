from __future__ import annotations

import importlib.metadata
import platform
from typing import Any


PROVIDER_MAP = {
    'cpu': 'CPUExecutionProvider',
    'cuda': 'CUDAExecutionProvider',
    'directml': 'DmlExecutionProvider',
    'coreml': 'CoreMLExecutionProvider',
}


def _distribution_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ('onnxruntime', 'onnxruntime-directml', 'onnxruntime-gpu'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


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
        'schema_version': 1,
        'runtime_version': ort.__version__,
        'runtime_device': ort.get_device(),
        'platform': platform.system().lower(),
        'machine': platform.machine().lower(),
        'available_providers': available,
        'provider_support': support,
        'distributions': _distribution_versions(),
    }
