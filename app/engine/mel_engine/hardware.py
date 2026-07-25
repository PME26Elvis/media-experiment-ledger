from __future__ import annotations

import json
import os
import platform
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from .providers import (
    PROVIDER_MAP,
    create_session_options,
    prepare_runtime,
    provider_inventory,
    provider_plan,
)


def _varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            output.append(byte | 0x80)
        else:
            output.append(byte)
            return bytes(output)


def _field_varint(number: int, value: int) -> bytes:
    return _varint(number << 3) + _varint(value)


def _field_bytes(number: int, value: bytes) -> bytes:
    return _varint((number << 3) | 2) + _varint(len(value)) + value


def _field_string(number: int, value: str) -> bytes:
    return _field_bytes(number, value.encode('utf-8'))


def _message(number: int, value: bytes) -> bytes:
    return _field_bytes(number, value)


def _dimension(value: int) -> bytes:
    return _field_varint(1, value)


def _value_info(name: str, shape: tuple[int, ...]) -> bytes:
    tensor_shape = b''.join(_message(1, _dimension(value)) for value in shape)
    tensor_type = _field_varint(1, 1) + _message(2, tensor_shape)
    type_proto = _message(1, tensor_type)
    return _field_string(1, name) + _message(2, type_proto)


def tiny_identity_model() -> bytes:
    """Return a dependency-free ONNX Identity graph for provider self-tests."""
    node = _field_string(1, 'input') + _field_string(2, 'output') + _field_string(4, 'Identity')
    graph = (
        _message(1, node)
        + _field_string(2, 'mel-hardware-self-test')
        + _message(11, _value_info('input', (1, 4)))
        + _message(12, _value_info('output', (1, 4)))
    )
    opset = _field_varint(2, 13)
    return (
        _field_varint(1, 8)
        + _field_string(2, 'media-experiment-ledger')
        + _message(7, graph)
        + _message(8, opset)
    )


def _profile_provider_counts(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    counts: dict[str, int] = {}
    for event in payload:
        provider = (event.get('args') or {}).get('provider')
        if isinstance(provider, str) and provider:
            counts[provider] = counts.get(provider, 0) + 1
    return dict(sorted(counts.items()))


def _directory_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {'path': str(path), 'size_bytes': 0, 'file_count': 0}
    size = 0
    count = 0
    for item in path.rglob('*'):
        if item.is_file():
            try:
                size += item.stat().st_size
                count += 1
            except OSError:
                continue
    return {'path': str(path), 'size_bytes': size, 'file_count': count}


def _memory_snapshot() -> dict[str, int]:
    if os.name == 'nt':
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ('length', ctypes.c_ulong),
                    ('memory_load', ctypes.c_ulong),
                    ('total_physical', ctypes.c_ulonglong),
                    ('available_physical', ctypes.c_ulonglong),
                    ('total_page_file', ctypes.c_ulonglong),
                    ('available_page_file', ctypes.c_ulonglong),
                    ('total_virtual', ctypes.c_ulonglong),
                    ('available_virtual', ctypes.c_ulonglong),
                    ('available_extended_virtual', ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {
                    'total_bytes': int(status.total_physical),
                    'available_bytes': int(status.available_physical),
                }
        except Exception:
            pass
    try:
        page_size = int(os.sysconf('SC_PAGE_SIZE'))
        total_pages = int(os.sysconf('SC_PHYS_PAGES'))
        available_pages = int(os.sysconf('SC_AVPHYS_PAGES'))
        return {
            'total_bytes': page_size * total_pages,
            'available_bytes': page_size * available_pages,
        }
    except (AttributeError, OSError, ValueError):
        return {'total_bytes': 0, 'available_bytes': 0}


def hardware_diagnostics() -> dict[str, Any]:
    inventory = provider_inventory()
    inventory['host_memory'] = _memory_snapshot()
    inventory['cpu'] = {
        'logical_cores': os.cpu_count() or 1,
        'processor': platform.processor() or platform.machine(),
    }
    return inventory


def run_provider_self_test(request: dict[str, Any]) -> dict[str, Any]:
    provider_key = str(request.get('provider') or 'cpu').lower()
    if provider_key not in PROVIDER_MAP:
        raise ValueError(f'Unsupported provider: {provider_key}')
    device_id = max(0, int(request.get('device_id') or 0))
    allow_cpu_fallback = bool(request.get('allow_cpu_fallback', True))
    compute_units = str(request.get('coreml_compute_units') or 'ALL').upper()
    warm_runs = min(20, max(1, int(request.get('warm_runs') or 5)))
    requested_name = PROVIDER_MAP[provider_key]
    evidence: dict[str, Any] = {
        'schema_version': 1,
        'requested_provider': provider_key,
        'requested_provider_name': requested_name,
        'device_id': device_id,
        'allow_cpu_fallback': allow_cpu_fallback,
        'coreml_compute_units': compute_units,
        'registered': False,
        'session_created': False,
        'assigned_node_count': 0,
        'cpu_assigned_node_count': 0,
        'fallback_detected': False,
        'passed': False,
        'status': 'error',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    try:
        import onnxruntime as ort

        prepare_runtime(ort, requested_name)
        available = list(ort.get_available_providers())
        evidence.update({
            'runtime_version': ort.__version__,
            'available_providers': available,
            'registered': requested_name in available,
        })
        if requested_name not in available:
            evidence['status'] = 'unavailable'
            evidence['recommendation'] = 'Install or select a runtime bundle that registers the requested execution provider.'
            return evidence

        with tempfile.TemporaryDirectory(prefix='mel-hardware-self-test-') as directory:
            root = Path(directory)
            model_path = root / 'identity.onnx'
            model_path.write_bytes(tiny_identity_model())
            plan = provider_plan(
                provider_key,
                available,
                allow_cpu_fallback=allow_cpu_fallback,
                model_path=model_path,
                device_id=device_id,
                coreml_compute_units=compute_units,
            )
            options = create_session_options(
                ort,
                primary_provider=str(plan['active_provider']),
                allow_cpu_fallback=allow_cpu_fallback,
                profile_prefix=root / 'provider-profile',
            )
            started = time.perf_counter()
            session = ort.InferenceSession(str(model_path), sess_options=options, providers=plan['providers'])
            evidence['cold_start_ms'] = round((time.perf_counter() - started) * 1000, 3)
            evidence['session_created'] = True
            evidence['active_provider'] = str(plan['active_provider'])
            tensor = np.asarray([[0.25, -1.5, 2.0, 8.25]], dtype=np.float32)
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            started = time.perf_counter()
            cold = np.asarray(session.run([output_name], {input_name: tensor})[0])
            evidence['cold_inference_ms'] = round((time.perf_counter() - started) * 1000, 3)
            warm_times: list[float] = []
            warm = cold
            for _ in range(warm_runs):
                started = time.perf_counter()
                warm = np.asarray(session.run([output_name], {input_name: tensor})[0])
                warm_times.append((time.perf_counter() - started) * 1000)
            evidence['warm_inference_ms'] = round(sum(warm_times) / len(warm_times), 3)
            evidence['warm_runs'] = warm_runs
            profile_path = Path(session.end_profiling())
            counts = _profile_provider_counts(profile_path)
            assigned = int(counts.get(requested_name, 0))
            cpu_assigned = int(counts.get('CPUExecutionProvider', 0))
            fallback = requested_name != 'CPUExecutionProvider' and cpu_assigned > 0
            valid_output = cold.shape == tensor.shape and warm.shape == tensor.shape and bool(np.isfinite(warm).all()) and bool(np.allclose(warm, tensor))
            evidence.update({
                'profile_provider_nodes': counts,
                'assigned_node_count': assigned,
                'cpu_assigned_node_count': cpu_assigned,
                'fallback_detected': fallback,
            })
            if requested_name == 'CPUExecutionProvider':
                passed = valid_output and cpu_assigned > 0
            else:
                passed = valid_output and assigned > 0 and (allow_cpu_fallback or not fallback)
            evidence['passed'] = passed
            evidence['status'] = 'passed' if passed and not fallback else 'fallback' if valid_output and fallback else 'error'
            if fallback:
                evidence['recommendation'] = 'The provider is registered, but this graph used CPU nodes. Review driver/operator support or disable CPU fallback for strict qualification.'
            elif not passed:
                evidence['recommendation'] = 'The session was created but did not produce valid provider-assignment evidence.'
            if provider_key == 'coreml':
                cache_path = model_path.parent / '.mel-provider-cache' / 'coreml'
                evidence['cache'] = _directory_summary(cache_path)
    except Exception as error:
        evidence['status'] = 'error'
        evidence['error'] = {'name': type(error).__name__, 'message': str(error)}
        evidence['recommendation'] = 'Review the runtime bundle, driver, provider options and support evidence before starting a corpus job.'
    return evidence


def clear_provider_cache(request: dict[str, Any]) -> dict[str, Any]:
    provider = str(request.get('provider') or '').lower()
    raw = str(request.get('cache_path') or '')
    path = Path(raw).expanduser().resolve() if raw else Path.cwd() / '.mel-provider-cache' / provider
    summary = _directory_summary(path)
    if path.exists():
        shutil.rmtree(path)
    return {'cleared': True, 'path': str(path), 'removed_bytes': int(summary['size_bytes'])}
