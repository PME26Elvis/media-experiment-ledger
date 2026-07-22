from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
from PIL import Image, ImageOps

from .common import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, emit, iter_media, read_json, sha256, write_json

PROXY_EDGES = (160, 320, 640, 1280)
DEFAULT_COPY_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024


def image_metadata(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        source.load()
        return {
            'width': source.width,
            'height': source.height,
            'format': source.format,
            'frames': int(getattr(source, 'n_frames', 1)),
        }


def video_poster(path: Path) -> tuple[Image.Image, dict[str, Any]]:
    if path.suffix.lower() == '.gif':
        with Image.open(path) as source:
            source.seek(0)
            poster = source.convert('RGB').copy()
            frames = int(getattr(source, 'n_frames', 1))
            duration_ms = int(source.info.get('duration') or 0)
            return poster, {
                'width': poster.width,
                'height': poster.height,
                'format': 'GIF',
                'frames': frames,
                'duration_seconds': round(frames * duration_ms / 1000, 6),
            }
    reader = imageio.get_reader(str(path), format='ffmpeg')
    try:
        metadata = reader.get_meta_data()
        array = reader.get_data(0)
        image = Image.fromarray(array[:, :, :3]).convert('RGB')
        frame_count = metadata.get('nframes')
        return image, {
            'width': image.width,
            'height': image.height,
            'format': path.suffix.lower().removeprefix('.'),
            'frames': int(frame_count) if frame_count not in (None, float('inf')) else None,
            'fps': float(metadata.get('fps') or 0) or None,
            'duration_seconds': float(metadata.get('duration') or 0) or None,
        }
    finally:
        reader.close()


def save_proxy(source: Image.Image, destination: Path, edge: int) -> dict[str, Any]:
    image = source.convert('RGB')
    image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    image.save(temporary, format='JPEG', quality=86, optimize=True, progressive=True)
    temporary.replace(destination)
    return {
        'edge': edge,
        'path': str(destination),
        'width': image.width,
        'height': image.height,
        'size_bytes': destination.stat().st_size,
        'sha256': sha256(destination),
    }


def materialize(source: Path, root: Path, digest: str) -> Path:
    destination = root / digest[:2] / f'{digest}{source.suffix.lower()}'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size != source.stat().st_size or sha256(destination) != digest:
            raise ValueError(f'content-addressed managed-copy collision: {destination}')
        return destination
    temporary = destination.with_suffix(destination.suffix + '.partial')
    temporary.unlink(missing_ok=True)
    try:
        os.link(source, temporary)
    except OSError:
        shutil.copy2(source, temporary)
    if sha256(temporary) != digest:
        temporary.unlink(missing_ok=True)
        raise ValueError(f'managed copy hash mismatch: {source}')
    temporary.replace(destination)
    return destination


def record_reusable(record: dict[str, Any], path: Path, stat: os.stat_result) -> bool:
    if str(record.get('source_path') or '') != str(path):
        return False
    if int(record.get('source_size_bytes') or -1) != stat.st_size or int(record.get('source_mtime_ns') or -1) != stat.st_mtime_ns:
        return False
    proxies = record.get('proxies')
    return isinstance(proxies, list) and all(Path(str(proxy.get('path') or '')).is_file() for proxy in proxies if isinstance(proxy, dict))


def process_media(path: Path, output: Path, effective_mode: str, previous: dict[str, Any] | None) -> dict[str, Any]:
    stat = path.stat()
    if previous and record_reusable(previous, path, stat):
        return {**previous, 'reused': True}

    media_type = 'image' if path.suffix.lower() in IMAGE_EXTENSIONS else 'video'
    digest = sha256(path)
    if media_type == 'image':
        metadata = image_metadata(path)
        with Image.open(path) as source:
            preview_source = ImageOps.exif_transpose(source).convert('RGB')
            preview_source.load()
    else:
        preview_source, metadata = video_poster(path)

    proxies = [
        save_proxy(preview_source, output / 'proxies' / digest[:2] / digest / f'{edge}.jpg', edge)
        for edge in PROXY_EDGES
    ]
    stored_path = str(path)
    if effective_mode == 'copy':
        stored_path = str(materialize(path, output / 'managed-media' / 'blobs', digest))
    return {
        'source_path': str(path),
        'stored_path': stored_path,
        'storage_mode': effective_mode,
        'media_type': media_type,
        'source_size_bytes': stat.st_size,
        'source_mtime_ns': stat.st_mtime_ns,
        'sha256': digest,
        'metadata': metadata,
        'proxies': proxies,
        'reused': False,
    }


def run_scan(request: dict[str, Any]) -> dict[str, Any]:
    files = iter_media([str(request.get('image_path', '')), str(request.get('video_path', ''))])
    output = Path(str(request.get('output_path') or '.')).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    total_bytes = sum(path.stat().st_size for path in files)
    free_bytes = shutil.disk_usage(output).free
    requested_mode = str(request.get('import_mode') or 'adaptive')
    if requested_mode not in {'adaptive', 'copy', 'reference'}:
        raise ValueError('import_mode must be adaptive, copy or reference')
    copy_threshold = max(0, int(request.get('copy_threshold_bytes') or DEFAULT_COPY_THRESHOLD_BYTES))
    effective_mode = requested_mode
    if requested_mode == 'adaptive':
        effective_mode = 'copy' if total_bytes <= copy_threshold and total_bytes * 1.25 <= free_bytes else 'reference'
    if effective_mode == 'copy' and total_bytes * 1.15 > free_bytes:
        raise ValueError(f'Insufficient disk space for managed copy: need about {round(total_bytes * 1.15)} bytes, have {free_bytes}')

    previous_manifest = read_json(output / 'media-index.json', {})
    previous_by_path = {
        str(record.get('source_path') or ''): record
        for record in previous_manifest.get('assets', [])
        if isinstance(record, dict)
    } if isinstance(previous_manifest, dict) else {}

    workers = min(8, max(1, int(request.get('workers') or min(4, os.cpu_count() or 2))))
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='media-import') as executor:
        futures = {
            executor.submit(process_media, path, output, effective_mode, previous_by_path.get(str(path))): path
            for path in files
        }
        for completed, future in enumerate(as_completed(futures), 1):
            path = futures[future]
            try:
                records.append(future.result())
            except Exception as error:
                errors.append({'path': str(path), 'error': f'{type(error).__name__}: {error}'})
            emit('progress', stage='indexing-and-proxies', progress=completed / max(len(files), 1) * 100, completed=completed, total=len(files))

    records.sort(key=lambda record: (record['media_type'], record['source_path']))
    unique_hashes = len({record['sha256'] for record in records})
    manifest = {
        'schema_version': 2,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'requested_storage_mode': requested_mode,
        'effective_storage_mode': effective_mode,
        'source_count': len(files),
        'indexed_count': len(records),
        'error_count': len(errors),
        'source_bytes': total_bytes,
        'free_bytes_before_import': free_bytes,
        'estimated_copy_bytes': round(total_bytes * 1.15),
        'unique_content_count': unique_hashes,
        'duplicate_content_count': max(0, len(records) - unique_hashes),
        'proxy_edges': list(PROXY_EDGES),
        'worker_count': workers,
        'assets': records,
        'errors': errors,
    }
    write_json(output / 'media-index.json', manifest)
    write_json(output / 'portable-project.json', {
        'schema_version': 1,
        'media_index': 'media-index.json',
        'storage_mode': effective_mode,
        'portable': effective_mode == 'copy',
        'managed_media_root': 'managed-media/blobs' if effective_mode == 'copy' else None,
        'proxy_root': 'proxies',
        'source_roots': [value for value in [request.get('image_path'), request.get('video_path')] if value],
    })
    return manifest
