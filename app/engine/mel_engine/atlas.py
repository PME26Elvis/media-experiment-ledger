from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .common import IMAGE_EXTENSIONS, emit, iter_media, sha256, write_json


def run_atlas(request: dict[str, Any]) -> dict[str, Any]:
    files = [p for p in iter_media([str(request.get('input_path', ''))]) if p.suffix.lower() in IMAGE_EXTENSIONS]
    output = Path(str(request.get('output_path') or '.')).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    cell = 480
    columns = 2
    pages: list[dict[str, Any]] = []
    for page_index, start in enumerate(range(0, len(files), 4), 1):
        selected = files[start:start + 4]
        canvas = Image.new('RGB', (columns * cell, columns * cell + 80), '#10182a')
        draw = ImageDraw.Draw(canvas)
        for offset, path in enumerate(selected):
            with Image.open(path) as source:
                source = source.convert('RGB')
                source.thumbnail((cell - 24, cell - 64))
                x = (offset % columns) * cell + (cell - source.width) // 2
                y = (offset // columns) * cell + 20
                canvas.paste(source, (x, y))
                draw.text(((offset % columns) * cell + 16, (offset // columns) * cell + cell - 36), path.name[:54], fill='#dbe4ff')
        draw.text((18, columns * cell + 24), f'Media Experiment Ledger Studio · page {page_index}', fill='#7c8cff')
        page_path = output / f'atlas-page-{page_index:03d}.jpg'
        canvas.save(page_path, quality=91, optimize=True)
        pages.append({'path': str(page_path), 'sha256': sha256(page_path), 'sources': [str(p) for p in selected]})
        emit('progress', stage='rendering', progress=min(100, (start + len(selected)) / max(len(files), 1) * 100), completed=start + len(selected), total=len(files))
    manifest = {'schema_version': 1, 'template': request.get('template'), 'source_count': len(files), 'pages': pages, 'video_pdf_mode': request.get('video_pdf_mode', 'three-frame-strip')}
    write_json(output / 'atlas-manifest.json', manifest)
    return manifest
