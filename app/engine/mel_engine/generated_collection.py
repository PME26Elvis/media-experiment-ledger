from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
from PIL import Image

from .common import sha256, write_json


def slug(value: str) -> str:
    safe = re.sub(r'[^A-Za-z0-9._-]+', '-', value).strip('-._').lower()[:96]
    return safe or 'generated-media'


def validate_media(path: Path, media_type: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError('media file is missing or empty')
    if media_type == 'image':
        with Image.open(path) as source:
            source.verify()
        with Image.open(path) as source:
            source.load()
            return {
                'width': source.width,
                'height': source.height,
                'format': source.format,
                'frames': int(getattr(source, 'n_frames', 1)),
            }
    if path.suffix.lower() == '.gif':
        with Image.open(path) as source:
            source.seek(0)
            source.load()
            return {
                'width': source.width,
                'height': source.height,
                'format': source.format,
                'frames': int(getattr(source, 'n_frames', 1)),
                'duration_seconds': round(int(source.info.get('duration') or 0) * int(getattr(source, 'n_frames', 1)) / 1000, 6),
            }
    reader = imageio.get_reader(str(path), format='ffmpeg')
    try:
        metadata = reader.get_meta_data()
        frame = reader.get_data(0)
        if frame.ndim != 3 or frame.shape[0] <= 0 or frame.shape[1] <= 0:
            raise ValueError(f'invalid first video frame shape: {frame.shape}')
        return {
            'width': int(frame.shape[1]),
            'height': int(frame.shape[0]),
            'format': path.suffix.lower().removeprefix('.'),
            'frames': int(metadata.get('nframes') or 0) if metadata.get('nframes') not in (None, float('inf')) else None,
            'fps': float(metadata.get('fps') or 0) or None,
            'duration_seconds': float(metadata.get('duration') or 0) or None,
        }
    finally:
        reader.close()


def materialize_blob(source: Path, root: Path, digest: str) -> Path:
    suffix = source.suffix.lower() or '.bin'
    destination = root / digest[:2] / f'{digest}{suffix}'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size != source.stat().st_size or sha256(destination) != digest:
            raise ValueError(f'content-addressed blob collision: {destination}')
        return destination
    temporary = destination.with_suffix(destination.suffix + '.partial')
    temporary.unlink(missing_ok=True)
    try:
        os.link(source, temporary)
    except OSError:
        shutil.copy2(source, temporary)
    if sha256(temporary) != digest:
        temporary.unlink(missing_ok=True)
        raise ValueError(f'blob materialization hash mismatch: {source}')
    temporary.replace(destination)
    return destination


def finalize_generated_collection(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    output = Path(str(request.get('output_path') or '.')).expanduser().resolve()
    completed = dict(result.get('completed') or {})
    collection_root = output / 'generated-media'
    blob_root = collection_root / 'blobs'
    quarantine_root = output / 'quarantine'
    records: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    for prompt_id, record_value in sorted(completed.items()):
        record = dict(record_value) if isinstance(record_value, dict) else {}
        local = dict(record.get('local') or {})
        local_path = str(local.get('path') or '')
        if not local_path:
            quarantined.append({'prompt_id': prompt_id, 'reason': 'no downloaded local media'})
            continue
        source = Path(local_path).resolve()
        try:
            expected = str(local.get('sha256') or '')
            actual = sha256(source)
            if expected and expected != actual:
                raise ValueError(f'download receipt hash mismatch: expected {expected}, got {actual}')
            metadata = validate_media(source, str(record.get('media_type') or request.get('media_type') or 'image'))
            blob = materialize_blob(source, blob_root, actual)
            records.append({
                'prompt_id': str(prompt_id),
                'prompt_sha256': str(record.get('prompt_sha256') or ''),
                'category': str(record.get('category') or 'uncategorized'),
                'media_type': str(record.get('media_type') or request.get('media_type') or 'image'),
                'model': str(record.get('model') or request.get('model') or ''),
                'blob_path': str(blob),
                'sha256': actual,
                'size_bytes': blob.stat().st_size,
                'source_url': record.get('output_url'),
                'metadata': metadata,
                'completed_at': record.get('completed_at'),
            })
        except Exception as error:
            quarantine_root.mkdir(parents=True, exist_ok=True)
            quarantine = quarantine_root / f'{slug(prompt_id)}-{source.name}'
            try:
                if source.exists():
                    if quarantine.exists():
                        quarantine = quarantine_root / f'{slug(prompt_id)}-{sha256(source)[:12]}-{source.name}'
                    shutil.move(str(source), quarantine)
            except OSError:
                quarantine = source
            quarantined.append({
                'prompt_id': str(prompt_id),
                'source_path': str(source),
                'quarantine_path': str(quarantine),
                'reason': f'{type(error).__name__}: {error}',
            })

    collection = {
        'schema_version': 1,
        'kind': 'generated-media-collection',
        'provider': request.get('provider'),
        'model': request.get('model'),
        'media_type': request.get('media_type'),
        'automation_fingerprint': result.get('fingerprint'),
        'valid_asset_count': len(records),
        'quarantined_asset_count': len(quarantined),
        'assets': records,
        'quarantined': quarantined,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    collection_path = collection_root / 'collection-manifest.json'
    write_json(collection_path, collection)

    named_corpus: dict[str, Any] | None = None
    if bool(request.get('auto_enroll_named_corpus')) and str(request.get('collection_name') or '').strip():
        name = str(request['collection_name']).strip()
        named_root = output / 'named-corpora' / slug(name)
        named_corpus = {
            'schema_version': 1,
            'kind': 'named-local-corpus',
            'name': name,
            'enrollment_rule': 'verified-success-only',
            'source_collection': str(collection_path),
            'asset_count': len(records),
            'assets': [
                {
                    'sha256': record['sha256'],
                    'blob_path': record['blob_path'],
                    'media_type': record['media_type'],
                    'prompt_id': record['prompt_id'],
                }
                for record in records
            ],
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        write_json(named_root / 'manifest.json', named_corpus)

    updated = dict(result)
    updated['generated_media_collection'] = {
        'manifest_path': str(collection_path),
        'valid_asset_count': len(records),
        'quarantined_asset_count': len(quarantined),
        'named_corpus_path': str(output / 'named-corpora' / slug(str(request.get('collection_name') or ''))) if named_corpus else None,
    }
    if quarantined:
        updated['status'] = 'completed_with_quarantine'
    return updated
