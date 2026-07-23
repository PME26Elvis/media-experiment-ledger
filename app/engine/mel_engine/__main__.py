from __future__ import annotations

import json
import sys
from typing import Any

from .atlas import run_atlas
from .automation import run_automation
from .common import emit
from .detection import run_detection
from .download import run_sample_download
from .generated_collection import finalize_generated_collection
from .providers import provider_inventory
from .scan import run_scan


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get('operation')
    if operation == 'scan':
        return run_scan(request)
    if operation == 'atlas':
        return run_atlas(request)
    if operation == 'detection':
        return run_detection(request)
    if operation == 'automation':
        return finalize_generated_collection(request, run_automation(request))
    if operation == 'sample-download':
        return run_sample_download(request)
    if operation == 'providers':
        return provider_inventory()
    if operation == 'pdf-export':
        return {'status': 'document-export-delegated-to-electron-print-pipeline'}
    raise ValueError(f'Unsupported operation: {operation}')


def main() -> int:
    try:
        request = json.loads(sys.stdin.readline())
        emit('progress', stage='validated', progress=0, completed=0, total=0)
        result = dispatch(request)
        emit('result', data=result)
        return 0
    except Exception as error:
        emit('error', message=f'{type(error).__name__}: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
