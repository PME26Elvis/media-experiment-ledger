from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
VIDEO_EXTENSIONS = {'.gif', '.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi'}
EventSink = Callable[..., None]


def emit(kind: str, **payload: Any) -> None:
    print(json.dumps({'type': kind, **payload}, ensure_ascii=False), flush=True)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def iter_media(paths: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    supported = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    for raw in paths:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if path.is_file() and path.suffix.lower() in supported:
            result.append(path)
        elif path.is_dir():
            result.extend(
                candidate
                for candidate in path.rglob('*')
                if candidate.is_file() and candidate.suffix.lower() in supported
            )
    return sorted(set(result), key=lambda candidate: str(candidate).lower())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def json_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default
