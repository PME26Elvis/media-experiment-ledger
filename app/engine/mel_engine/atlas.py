from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

from .common import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, emit, iter_media, json_fingerprint, read_json, sha256, write_json


CELL = 480
COLUMNS = 2
PAGE_BACKGROUND = '#10182a'
PAGE_FOREGROUND = '#dbe4ff'
PAGE_ACCENT = '#7c8cff'


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size=size)
    except OSError:
        return ImageFont.load_default()


def _fit_image(path: Path, maximum: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail(maximum, Image.Resampling.LANCZOS)
        return image.copy()


def _save_jpeg(image: Image.Image, path: Path, quality: int = 91) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    image.save(temporary, format='JPEG', quality=quality, optimize=True, progressive=True)
    temporary.replace(path)
    return {'path': str(path), 'sha256': sha256(path), 'size_bytes': path.stat().st_size}


def _save_gif(frames: list[Image.Image], path: Path, duration_ms: int = 850) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    palette_frames = [frame.convert('P', palette=Image.Palette.ADAPTIVE, colors=192) for frame in frames]
    palette_frames[0].save(
        temporary,
        format='GIF',
        save_all=True,
        append_images=palette_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )
    temporary.replace(path)
    return {'path': str(path), 'sha256': sha256(path), 'size_bytes': path.stat().st_size}


def _canvas(title: str, subtitle: str, *, width: int = COLUMNS * CELL, height: int = COLUMNS * CELL + 100) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new('RGB', (width, height), PAGE_BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((18, height - 72), title, fill=PAGE_ACCENT, font=_font(22))
    draw.text((18, height - 42), subtitle, fill=PAGE_FOREGROUND, font=_font(15))
    return canvas, draw


def _render_image_page(selected: list[Path], page_index: int, output: Path) -> dict[str, Any]:
    canvas, draw = _canvas(
        f'Media Experiment Ledger Studio · image page {page_index}',
        f'{len(selected)} source image(s)',
    )
    sources: list[dict[str, Any]] = []
    for offset, path in enumerate(selected):
        image = _fit_image(path, (CELL - 24, CELL - 72))
        x = (offset % COLUMNS) * CELL + (CELL - image.width) // 2
        y = (offset // COLUMNS) * CELL + 20
        canvas.paste(image, (x, y))
        label_y = (offset // COLUMNS) * CELL + CELL - 40
        draw.text(((offset % COLUMNS) * CELL + 16, label_y), path.name[:54], fill=PAGE_FOREGROUND, font=_font(15))
        sources.append({'path': str(path), 'sha256': sha256(path), 'size_bytes': path.stat().st_size})
    page_path = output / 'pages' / f'atlas-image-page-{page_index:03d}.jpg'
    page = _save_jpeg(canvas, page_path)
    return {**page, 'media_type': 'image', 'sources': sources}


def _gif_frames(path: Path, percentages: tuple[float, ...]) -> tuple[list[Image.Image], dict[str, Any]]:
    with Image.open(path) as source:
        raw = [ImageOps.exif_transpose(frame.copy()).convert('RGB') for frame in ImageSequence.Iterator(source)]
        if not raw:
            raise ValueError(f'GIF contains no decodable frames: {path}')
        indexes = [min(len(raw) - 1, max(0, round((len(raw) - 1) * percentage))) for percentage in percentages]
        duration_ms = int(source.info.get('duration') or 100)
        return [raw[index] for index in indexes], {
            'frame_count': len(raw),
            'fps': round(1000 / duration_ms, 6) if duration_ms > 0 else None,
            'duration_seconds': round(len(raw) * duration_ms / 1000, 6),
            'selected_frame_indexes': indexes,
        }


def _video_frames(path: Path, percentages: tuple[float, ...]) -> tuple[list[Image.Image], dict[str, Any]]:
    reader = imageio.get_reader(str(path), format='ffmpeg')
    try:
        metadata = reader.get_meta_data()
        fps = float(metadata.get('fps') or 0.0)
        duration = float(metadata.get('duration') or 0.0)
        frame_count_raw = metadata.get('nframes')
        frame_count = int(frame_count_raw) if frame_count_raw not in (None, float('inf')) else 0
        if frame_count <= 0 and fps > 0 and duration > 0:
            frame_count = max(1, round(fps * duration))
        if frame_count <= 0:
            frame_count = int(reader.count_frames())
        indexes = [min(frame_count - 1, max(0, round((frame_count - 1) * percentage))) for percentage in percentages]
        frames: list[Image.Image] = []
        for index in indexes:
            array = np.asarray(reader.get_data(index))
            if array.ndim != 3 or array.shape[2] < 3:
                raise ValueError(f'Unexpected video frame shape {array.shape} in {path}')
            frames.append(Image.fromarray(array[:, :, :3].astype(np.uint8), mode='RGB'))
        timestamps = [round(index / fps, 6) if fps > 0 else None for index in indexes]
        return frames, {
            'frame_count': frame_count,
            'fps': round(fps, 6) if fps > 0 else None,
            'duration_seconds': round(duration, 6) if duration > 0 else (round(frame_count / fps, 6) if fps > 0 else None),
            'selected_frame_indexes': indexes,
            'selected_timestamps_seconds': timestamps,
        }
    finally:
        reader.close()


def extract_video_evidence(path: Path, output: Path, *, create_gif_preview: bool = True) -> dict[str, Any]:
    percentages = (0.10, 0.50, 0.90)
    frames, metadata = _gif_frames(path, percentages) if path.suffix.lower() == '.gif' else _video_frames(path, percentages)
    normalized: list[Image.Image] = []
    for frame in frames:
        image = frame.convert('RGB')
        image.thumbnail((760, 428), Image.Resampling.LANCZOS)
        normalized.append(image)

    strip_width = max(frame.width for frame in normalized)
    strip_height = max(frame.height for frame in normalized)
    strip = Image.new('RGB', (strip_width * 3, strip_height + 66), PAGE_BACKGROUND)
    draw = ImageDraw.Draw(strip)
    for index, (frame, percentage) in enumerate(zip(normalized, percentages, strict=True)):
        x = index * strip_width + (strip_width - frame.width) // 2
        strip.paste(frame, (x, 0))
        label = f'{round(percentage * 100)}%'
        timestamp = metadata.get('selected_timestamps_seconds', [None, None, None])[index] if metadata.get('selected_timestamps_seconds') else None
        if timestamp is not None:
            label += f' · {timestamp:.2f}s'
        draw.text((index * strip_width + 16, strip_height + 20), label, fill=PAGE_FOREGROUND, font=_font(18))

    source_digest = sha256(path)
    stem = f'{path.stem[:72]}-{source_digest[:12]}'
    strip_record = _save_jpeg(strip, output / 'video-evidence' / f'{stem}-strip.jpg', quality=90)
    poster_record = _save_jpeg(normalized[1], output / 'video-evidence' / f'{stem}-poster.jpg', quality=90)
    gif_record: dict[str, Any] | None = None
    if create_gif_preview:
        gif_record = _save_gif(normalized, output / 'video-evidence' / f'{stem}-preview.gif')
    return {
        'source': {'path': str(path), 'sha256': source_digest, 'size_bytes': path.stat().st_size},
        'percentages': list(percentages),
        **metadata,
        'strip': strip_record,
        'poster': poster_record,
        'gif_preview': gif_record,
    }


def _render_video_page(evidence: dict[str, Any], page_index: int, output: Path) -> dict[str, Any]:
    strip_path = Path(str(evidence['strip']['path']))
    strip = _fit_image(strip_path, (COLUMNS * CELL - 48, COLUMNS * CELL - 150))
    canvas, draw = _canvas(
        f'Media Experiment Ledger Studio · video page {page_index}',
        Path(str(evidence['source']['path'])).name[:90],
    )
    x = (canvas.width - strip.width) // 2
    y = 24
    canvas.paste(strip, (x, y))
    duration = evidence.get('duration_seconds')
    fps = evidence.get('fps')
    details = f"frames={evidence.get('frame_count')} · duration={duration if duration is not None else 'unknown'}s · fps={fps if fps is not None else 'unknown'}"
    draw.text((18, canvas.height - 104), details, fill=PAGE_FOREGROUND, font=_font(15))
    page = _save_jpeg(canvas, output / 'pages' / f'atlas-video-page-{page_index:03d}.jpg')
    return {**page, 'media_type': 'video', 'source': evidence['source'], 'evidence': evidence}


def _valid_record(record: dict[str, Any]) -> bool:
    path = Path(str(record.get('path') or ''))
    return path.is_file() and str(record.get('sha256') or '') == sha256(path)


def run_atlas(request: dict[str, Any]) -> dict[str, Any]:
    discovered = iter_media([str(request.get('input_path', ''))])
    images = [path for path in discovered if path.suffix.lower() in IMAGE_EXTENSIONS]
    videos = [path for path in discovered if path.suffix.lower() in VIDEO_EXTENSIONS or path.suffix.lower() == '.gif']
    output = Path(str(request.get('output_path') or '.')).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    inventory = [
        {'path': str(path), 'sha256': sha256(path), 'size_bytes': path.stat().st_size, 'media_type': 'image' if path in images else 'video'}
        for path in discovered
    ]
    fingerprint = json_fingerprint({
        'inventory': inventory,
        'template': request.get('template'),
        'scope': request.get('scope'),
        'video_pdf_mode': request.get('video_pdf_mode', 'three-frame-strip'),
        'gif_preview': bool(request.get('create_gif_preview', True)),
    })
    state_path = output / 'atlas-state.json'
    state = read_json(state_path, {})
    if not isinstance(state, dict) or state.get('fingerprint') != fingerprint:
        state = {'schema_version': 2, 'fingerprint': fingerprint, 'image_pages': [], 'video_evidence': {}, 'video_pages': {}, 'warnings': []}
        write_json(state_path, state)

    image_pages: list[dict[str, Any]] = []
    previous_image_pages = list(state.get('image_pages') or [])
    for page_index, start in enumerate(range(0, len(images), 4), 1):
        selected = images[start : start + 4]
        cached = previous_image_pages[page_index - 1] if page_index - 1 < len(previous_image_pages) else None
        selected_hashes = [sha256(path) for path in selected]
        if isinstance(cached, dict) and cached.get('source_sha256') == selected_hashes and _valid_record(cached):
            page = cached
        else:
            page = _render_image_page(selected, page_index, output)
            page['source_sha256'] = selected_hashes
        image_pages.append(page)
        state['image_pages'] = image_pages
        write_json(state_path, state)
        completed = min(len(discovered), start + len(selected))
        emit('progress', stage='rendering-images', progress=completed / max(len(discovered), 1) * 100, completed=completed, total=len(discovered))

    video_evidence_by_sha: dict[str, Any] = dict(state.get('video_evidence') or {})
    video_pages_by_sha: dict[str, Any] = dict(state.get('video_pages') or {})
    warnings: list[str] = list(state.get('warnings') or [])
    for index, path in enumerate(videos, 1):
        source_digest = sha256(path)
        evidence = video_evidence_by_sha.get(source_digest)
        try:
            evidence_valid = isinstance(evidence, dict) and _valid_record(dict(evidence.get('strip') or {})) and _valid_record(dict(evidence.get('poster') or {}))
            if not evidence_valid:
                evidence = extract_video_evidence(path, output, create_gif_preview=bool(request.get('create_gif_preview', True)))
                video_evidence_by_sha[source_digest] = evidence
            page = video_pages_by_sha.get(source_digest)
            if not isinstance(page, dict) or not _valid_record(page):
                page = _render_video_page(evidence, index, output)
                video_pages_by_sha[source_digest] = page
        except Exception as error:
            warning = f'{path}: {type(error).__name__}: {error}'
            if warning not in warnings:
                warnings.append(warning)
        state['video_evidence'] = video_evidence_by_sha
        state['video_pages'] = video_pages_by_sha
        state['warnings'] = warnings
        write_json(state_path, state)
        completed = len(images) + index
        emit('progress', stage='rendering-videos', progress=completed / max(len(discovered), 1) * 100, completed=completed, total=len(discovered))

    video_evidence = [video_evidence_by_sha[key] for key in sorted(video_evidence_by_sha)]
    video_pages = [video_pages_by_sha[key] for key in sorted(video_pages_by_sha)]
    pages = [*image_pages, *video_pages]
    manifest = {
        'schema_version': 2,
        'fingerprint': fingerprint,
        'template': request.get('template'),
        'scope': request.get('scope'),
        'source_count': len(discovered),
        'image_source_count': len(images),
        'video_source_count': len(videos),
        'inventory': inventory,
        'pages': pages,
        'image_pages': image_pages,
        'video_pages': video_pages,
        'video_evidence': video_evidence,
        'video_pdf_mode': request.get('video_pdf_mode', 'three-frame-strip'),
        'warnings': warnings,
    }
    write_json(output / 'atlas-manifest.json', manifest)
    emit('progress', stage='verified', progress=100, completed=len(discovered), total=len(discovered))
    return manifest
