from __future__ import annotations

import json
import os
import sys
from typing import Any

from .atlas import run_atlas
from .automation import run_automation
from .common import emit
from .detection import run_detection, run_detection_benchmark
from .download import run_sample_download
from .generated_collection import finalize_generated_collection
from .hardware import clear_provider_cache, hardware_diagnostics, run_provider_self_test
from .providers import provider_inventory
from .scan import run_scan


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get('operation')
    if operation == 'scan':
        return run_scan(request)
    if operation == 'atlas':
        return run_atlas(request)
    if operation == 'detection':
        return run_detection_benchmark(request) if request.get('benchmark_mode') else run_detection(request)
    if operation == 'detection-benchmark':
        return run_detection_benchmark(request)
    if operation == 'automation':
        return finalize_generated_collection(request, run_automation(request))
    if operation == 'sample-download':
        return run_sample_download(request)
    if operation == 'providers':
        return provider_inventory()
    if operation == 'hardware-diagnostics':
        return hardware_diagnostics()
    if operation == 'provider-self-test':
        return run_provider_self_test(request)
    if operation == 'provider-cache-clear':
        return clear_provider_cache(request)
    if operation == 'pdf-export':
        return {'status': 'document-export-delegated-to-electron-print-pipeline'}
    raise ValueError(f'Unsupported operation: {operation}')


def process_line(line: str) -> bool:
    if not line.strip():
        return True
    try:
        request = json.loads(line)
        emit('progress', stage='validated', progress=0, completed=0, total=0)
        result = dispatch(request)
        emit('result', data=result)
        return True
    except Exception as error:
        emit('error', message=f'{type(error).__name__}: {error}')
        return False


def main() -> int:
    persistent = os.environ.get('MEL_ENGINE_PERSISTENT') == '1'
    if persistent:
        for line in sys.stdin:
            process_line(line)
        return 0
    line = sys.stdin.readline()
    return 0 if process_line(line) else 1


if __name__ == '__main__':
    raise SystemExit(main())
