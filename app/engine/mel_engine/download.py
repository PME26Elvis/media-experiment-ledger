from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

from .common import emit, sha256


def run_sample_download(request: dict[str, Any]) -> dict[str, Any]:
    url = str(request.get('url') or '')
    destination = Path(str(request.get('destination') or '')).resolve()
    expected_sha = str(request.get('sha256') or '').lower()
    if not url or not destination.name:
        raise ValueError('url and destination are required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=900) as response, partial.open('wb') as target:
        total = int(response.headers.get('content-length') or 0)
        done = 0
        while chunk := response.read(1024 * 1024):
            target.write(chunk)
            done += len(chunk)
            emit('progress', stage='downloading', progress=(done / total * 100) if total else 0, completed=done, total=total)
    actual_sha = sha256(partial)
    if expected_sha and actual_sha != expected_sha:
        partial.unlink(missing_ok=True)
        raise ValueError(f'download SHA-256 mismatch: expected {expected_sha}, got {actual_sha}')
    partial.replace(destination)
    return {'path': str(destination), 'size': destination.stat().st_size, 'sha256': actual_sha}
