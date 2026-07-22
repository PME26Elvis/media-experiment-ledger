from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

from .common import emit, sha256, write_json


def run_sample_download(request: dict[str, Any]) -> dict[str, Any]:
    url = str(request.get('url') or '')
    destination = Path(str(request.get('destination') or '')).resolve()
    expected_sha = str(request.get('sha256') or '').lower()
    expected_size = int(request.get('size_bytes') or 0)
    if not url or not destination.name:
        raise ValueError('url and destination are required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'Range': f'bytes={offset}-'} if offset else {}
    http_request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(http_request, timeout=900) as response, partial.open('ab' if offset and response.status == 206 else 'wb') as target:
        if offset and response.status != 206:
            offset = 0
        remaining = int(response.headers.get('content-length') or 0)
        total = expected_size or offset + remaining
        done = offset
        while chunk := response.read(1024 * 1024):
            target.write(chunk)
            done += len(chunk)
            emit('progress', stage='downloading', progress=(done / total * 100) if total else 0, completed=done, total=total)
    actual_size = partial.stat().st_size
    if expected_size and actual_size != expected_size:
        raise ValueError(f'download size mismatch: expected {expected_size}, got {actual_size}')
    actual_sha = sha256(partial)
    if expected_sha and actual_sha != expected_sha:
        partial.unlink(missing_ok=True)
        raise ValueError(f'download SHA-256 mismatch: expected {expected_sha}, got {actual_sha}')
    partial.replace(destination)
    receipt = {'schema_version': 1, 'path': str(destination), 'url': url, 'size': destination.stat().st_size, 'sha256': actual_sha, 'corpus_id': request.get('corpus_id'), 'asset_id': request.get('asset_id')}
    write_json(Path(f'{destination}.verified.json'), receipt)
    return receipt
