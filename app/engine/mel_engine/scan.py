from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import emit, iter_media, sha256, write_json


def run_scan(request: dict[str, Any]) -> dict[str, Any]:
    files = iter_media([str(request.get('image_path', '')), str(request.get('video_path', ''))])
    records: list[dict[str, Any]] = []
    total = len(files)
    for index, path in enumerate(files, 1):
        stat = path.stat()
        records.append({'path': str(path), 'media_type': 'image' if path.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'} else 'video', 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': sha256(path)})
        emit('progress', stage='indexing', progress=index / max(total, 1) * 100, completed=index, total=total)
    manifest = {'schema_version': 1, 'count': total, 'assets': records}
    output = request.get('output_path')
    if output:
        write_json(Path(str(output)) / 'media-index.json', manifest)
    return manifest
