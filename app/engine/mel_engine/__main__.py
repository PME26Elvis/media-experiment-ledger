from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Iterable

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi'}


def emit(kind: str, **payload: Any) -> None:
    print(json.dumps({'type': kind, **payload}, ensure_ascii=False), flush=True)


def iter_media(paths: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    for raw in paths:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            result.append(path)
        elif path.is_dir():
            result.extend(p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)
    return sorted(set(result), key=lambda p: str(p).lower())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def run_scan(request: dict[str, Any]) -> dict[str, Any]:
    files = iter_media([str(request.get('image_path', '')), str(request.get('video_path', ''))])
    records: list[dict[str, Any]] = []
    total = len(files)
    for index, path in enumerate(files, 1):
        stat = path.stat()
        records.append({'path': str(path), 'media_type': 'image' if path.suffix.lower() in IMAGE_EXTENSIONS else 'video', 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': sha256(path)})
        emit('progress', stage='indexing', progress=index / max(total, 1) * 100, completed=index, total=total)
    manifest = {'schema_version': 1, 'count': total, 'assets': records}
    output = request.get('output_path')
    if output:
        write_json(Path(str(output)) / 'media-index.json', manifest)
    return manifest


def run_atlas(request: dict[str, Any]) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont
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
        draw.text((18, columns * cell + 24), f"Media Experiment Ledger Studio · page {page_index}", fill='#7c8cff')
        page_path = output / f'atlas-page-{page_index:03d}.jpg'
        canvas.save(page_path, quality=91, optimize=True)
        pages.append({'path': str(page_path), 'sha256': sha256(page_path), 'sources': [str(p) for p in selected]})
        emit('progress', stage='rendering', progress=min(100, (start + len(selected)) / max(len(files), 1) * 100), completed=start + len(selected), total=len(files))
    manifest = {'schema_version': 1, 'template': request.get('template'), 'source_count': len(files), 'pages': pages, 'video_pdf_mode': request.get('video_pdf_mode', 'three-frame-strip')}
    write_json(output / 'atlas-manifest.json', manifest)
    return manifest


def run_detection(request: dict[str, Any]) -> dict[str, Any]:
    model_path = Path(str(request.get('model_path') or '')).expanduser()
    if not model_path.is_file():
        raise ValueError('A verified ONNX model_path is required. Model Manager must download or import the selected model first.')
    import numpy as np
    import onnxruntime as ort
    from PIL import Image
    provider_name = str(request.get('execution_provider', 'cpu'))
    provider_map = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'directml': 'DmlExecutionProvider', 'coreml': 'CoreMLExecutionProvider'}
    requested_provider = provider_map.get(provider_name, 'CPUExecutionProvider')
    available = ort.get_available_providers()
    providers = [requested_provider] if requested_provider in available else ['CPUExecutionProvider']
    session = ort.InferenceSession(str(model_path.resolve()), providers=providers)
    input_meta = session.get_inputs()[0]
    shape = input_meta.shape
    height = int(shape[2]) if len(shape) == 4 and isinstance(shape[2], int) else 416
    width = int(shape[3]) if len(shape) == 4 and isinstance(shape[3], int) else 416
    files = [p for p in iter_media([str(request.get('input_path', ''))]) if p.suffix.lower() in IMAGE_EXTENSIONS]
    output_dir = Path(str(request.get('output_path') or '.')).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, path in enumerate(files, 1):
        with Image.open(path) as image:
            original_size = image.size
            array = np.asarray(image.convert('RGB').resize((width, height)), dtype=np.float32) / 255.0
        tensor = np.transpose(array, (2, 0, 1))[None, ...]
        outputs = session.run(None, {input_meta.name: tensor})
        rows.append({'path': str(path), 'original_size': original_size, 'output_shapes': [list(np.asarray(value).shape) for value in outputs]})
        emit('progress', stage='inference', progress=index / max(len(files), 1) * 100, completed=index, total=len(files))
    manifest = {'schema_version': 1, 'model_path': str(model_path), 'model_sha256': sha256(model_path), 'providers': session.get_providers(), 'items': rows, 'note': 'Raw output-shape verification completed. Family-specific decode adapters are selected through the model registry.'}
    write_json(output_dir / 'detection-manifest.json', manifest)
    return manifest


def run_automation(request: dict[str, Any]) -> dict[str, Any]:
    if str(request.get('provider', 'agnes')).lower() != 'agnes':
        raise ValueError('Only the Agnes provider adapter is enabled in the initial registry.')
    api_key = os.environ.get('AGNES_API_KEY')
    if not api_key:
        raise ValueError('AGNES_API_KEY is not available to the engine process.')
    media_type = str(request.get('media_type', 'image'))
    prompt_source = Path(str(request.get('prompt_file') or ''))
    output = Path(str(request.get('output_path') or '.')).resolve(); output.mkdir(parents=True, exist_ok=True)
    prompts = [line.strip() for line in prompt_source.read_text(encoding='utf-8').splitlines() if line.strip()] if prompt_source.is_file() else []
    if not prompts:
        raise ValueError('Prompt file must contain at least one non-empty line.')
    endpoint = 'https://apihub.agnes-ai.com/v1/images/generations' if media_type == 'image' else 'https://apihub.agnes-ai.com/v1/videos'
    interval = max(0.0, float(request.get('interval_seconds', 90)))
    events = []
    for index, prompt in enumerate(prompts, 1):
        body = {'prompt': prompt, 'model': request.get('model') or ('agnes-image-2.1-flash' if media_type == 'image' else 'agnes-video-v2.0')}
        http_request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(http_request, timeout=900) as response:
            payload = json.loads(response.read().decode())
        events.append({'prompt': prompt, 'response': payload})
        emit('progress', stage='submitting', progress=index / len(prompts) * 100, completed=index, total=len(prompts))
        if index < len(prompts): time.sleep(interval)
    manifest = {'schema_version': 1, 'provider': 'agnes', 'media_type': media_type, 'events': events}
    write_json(output / 'automation-manifest.json', manifest)
    return manifest


def run_sample_download(request: dict[str, Any]) -> dict[str, Any]:
    url = str(request.get('url') or '')
    destination = Path(str(request.get('destination') or '')).resolve()
    if not url or not destination.name: raise ValueError('url and destination are required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=900) as response, destination.open('wb') as target:
        total = int(response.headers.get('content-length') or 0); done = 0
        while chunk := response.read(1024 * 1024):
            target.write(chunk); done += len(chunk); emit('progress', stage='downloading', progress=(done / total * 100) if total else 0, completed=done, total=total)
    return {'path': str(destination), 'size': destination.stat().st_size, 'sha256': sha256(destination)}


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get('operation')
    if operation == 'scan': return run_scan(request)
    if operation == 'atlas': return run_atlas(request)
    if operation == 'detection': return run_detection(request)
    if operation == 'automation': return run_automation(request)
    if operation == 'sample-download': return run_sample_download(request)
    if operation == 'pdf-export': return {'status': 'document-export-delegated-to-electron-print-pipeline'}
    raise ValueError(f'Unsupported operation: {operation}')


def main() -> int:
    try:
        line = sys.stdin.readline()
        request = json.loads(line)
        emit('progress', stage='validated', progress=0, completed=0, total=0)
        result = dispatch(request)
        emit('result', data=result)
        return 0
    except Exception as error:
        emit('error', message=f'{type(error).__name__}: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
