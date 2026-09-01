from __future__ import annotations

import csv
import math
import statistics
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

import imageio.v3 as iio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .common import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, emit, iter_media, json_fingerprint, read_json, sha256, write_json
from .providers import create_session_options, prepare_runtime, provider_name, provider_plan

_SESSION_CACHE: OrderedDict[str, tuple[Any, dict[str, Any], Any, list[str]]] = OrderedDict()
_MAX_SESSION_CACHE = 2


def clear_detection_session_cache() -> None:
    _SESSION_CACHE.clear()


def _load_vendor_modules():
    if getattr(sys, 'frozen', False):
        bundle_root = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        labels_path = bundle_root / 'mel_engine' / 'data' / 'coco-80.json'
    else:
        repository_root = Path(__file__).resolve().parents[3]
        vendor = repository_root / 'tools'
        labels_path = repository_root / 'object-detection' / 'coco-80.json'
        if str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
    import yolo_core  # type: ignore
    import nanodet_core  # type: ignore
    if not labels_path.is_file():
        raise FileNotFoundError(f'Detector labels are missing: {labels_path}')
    return yolo_core, nanodet_core, labels_path


def select_providers(
    requested: str,
    available: list[str],
    *,
    allow_cpu_fallback: bool = False,
) -> tuple[list[str], bool]:
    plan = provider_plan(requested, available, allow_cpu_fallback=allow_cpu_fallback)
    return list(plan['provider_names']), bool(plan['provider_fallback'])


def _nanodet_lock(width: int, height: int) -> dict[str, Any]:
    return {
        'input_width': width,
        'input_height': height,
        'strides': [8, 16, 32, 64],
        'reg_max': 7,
        'preprocess': {
            'color_order': 'BGR',
            'keep_ratio': False,
            'mean': [103.53, 116.28, 123.675],
            'std': [57.375, 57.12, 58.395],
        },
    }


def _session_for(
    ort: Any,
    model_path: Path,
    model_sha256: str,
    requested_provider: str,
    allow_provider_fallback: bool,
    device_id: int,
    coreml_compute_units: str,
) -> tuple[Any, dict[str, Any], Any, list[str], bool]:
    cache_key = json_fingerprint({
        'schema': 1,
        'model_sha256': model_sha256,
        'requested_provider': requested_provider,
        'allow_provider_fallback': allow_provider_fallback,
        'device_id': device_id,
        'coreml_compute_units': coreml_compute_units,
    })
    cached = _SESSION_CACHE.pop(cache_key, None)
    if cached is not None:
        _SESSION_CACHE[cache_key] = cached
        session, plan, input_meta, output_names = cached
        return session, plan, input_meta, output_names, True

    requested_provider_name = provider_name(requested_provider)
    prepare_runtime(ort, requested_provider_name)
    plan = provider_plan(
        requested_provider,
        list(ort.get_available_providers()),
        allow_cpu_fallback=allow_provider_fallback,
        model_path=model_path,
        device_id=device_id,
        coreml_compute_units=coreml_compute_units,
    )
    options = create_session_options(
        ort,
        primary_provider=str(plan['active_provider']),
        allow_cpu_fallback=allow_provider_fallback,
    )
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=plan['providers'])
    input_meta = session.get_inputs()[0]
    output_names = [item.name for item in session.get_outputs()]
    _SESSION_CACHE[cache_key] = (session, plan, input_meta, output_names)
    while len(_SESSION_CACHE) > _MAX_SESSION_CACHE:
        _SESSION_CACHE.popitem(last=False)
    return session, plan, input_meta, output_names, False


def _verified_model(request: dict[str, Any]) -> tuple[Path, str, str, int, int]:
    model_path = Path(str(request.get('model_path') or '')).expanduser().resolve()
    if not model_path.is_file():
        raise ValueError('A verified ONNX model_path is required. Model Manager must import the selected model first.')
    actual_model_sha = sha256(model_path)
    expected_model_sha = str(request.get('model_sha256') or '').lower()
    if expected_model_sha and actual_model_sha != expected_model_sha:
        raise ValueError(f'model SHA-256 changed after import: expected {expected_model_sha}, got {actual_model_sha}')
    adapter = str(request.get('adapter') or '')
    input_width = int(request.get('input_width') or 0)
    input_height = int(request.get('input_height') or 0)
    if input_width <= 0 or input_height <= 0:
        raise ValueError('model registry input_width and input_height are required')
    if adapter not in {'yolox-coco-v1', 'nanodet-plus-coco-v1'}:
        raise ValueError(f'unsupported detector adapter: {adapter}')
    return model_path, actual_model_sha, adapter, input_width, input_height


def _infer_image(
    image: Image.Image,
    *,
    adapter: str,
    input_width: int,
    input_height: int,
    confidence: float,
    nms_iou: float,
    max_detections: int,
    session: Any,
    input_meta: Any,
    output_names: list[str],
    labels: list[str],
    yolo_core: Any,
    nanodet_core: Any,
) -> tuple[list[Any], Image.Image, float]:
    started = time.perf_counter()
    if adapter == 'yolox-coco-v1':
        prepared = yolo_core.prepare_image(image, (input_height, input_width))
        raw_outputs = session.run(output_names, {input_meta.name: prepared.tensor})
        detections = yolo_core.postprocess_predictions(
            np.asarray(raw_outputs[0]), prepared, labels,
            confidence_threshold=confidence,
            nms_iou_threshold=nms_iou,
            max_detections=max_detections,
            input_size=(input_height, input_width),
        )
        source_image = prepared.image
    else:
        lock = _nanodet_lock(input_width, input_height)
        prepared = nanodet_core.prepare_image(image, lock)
        raw_outputs = session.run(output_names, {input_meta.name: prepared.tensor})
        detections = nanodet_core.postprocess_predictions(
            np.asarray(raw_outputs[0]), prepared, labels, lock,
            confidence_threshold=confidence,
            nms_iou_threshold=nms_iou,
            max_detections=max_detections,
        )
        source_image = prepared.image
    return detections, source_image, (time.perf_counter() - started) * 1000.0


def should_sample_frame(
    frame_index: int,
    *,
    source_fps: float,
    every_n_frames: int = 1,
    target_fps: float = 0.0,
) -> bool:
    if frame_index < 0:
        return False
    interval = max(1, int(every_n_frames))
    if target_fps > 0 and source_fps > 0:
        interval = max(interval, max(1, round(source_fps / min(target_fps, source_fps))))
    return frame_index % interval == 0


def _video_metadata(path: Path) -> dict[str, Any]:
    try:
        raw = iio.immeta(path)
    except Exception:
        raw = {}
    fps_value = raw.get('fps') or raw.get('framerate') or 30.0
    try:
        fps = float(fps_value)
    except (TypeError, ValueError):
        fps = 30.0
    if not math.isfinite(fps) or fps <= 0:
        fps = 30.0
    frame_count_value = raw.get('nframes') or raw.get('n_frames') or raw.get('duration_frames') or 0
    try:
        frame_count = int(frame_count_value)
    except (TypeError, ValueError, OverflowError):
        frame_count = 0
    return {
        'fps': fps,
        'frame_count': max(0, frame_count),
        'duration_seconds': float(raw.get('duration') or 0.0),
        'codec': str(raw.get('codec') or raw.get('codec_name') or ''),
    }


def _annotate_full_resolution(yolo_core: Any, image: Image.Image, detections: Iterable[Any]) -> Image.Image:
    preview = image.convert('RGB').copy()
    draw = ImageDraw.Draw(preview)
    font = ImageFont.load_default()
    line_width = max(2, round(min(preview.size) / 220))
    detections_list = list(detections)
    for detection in detections_list:
        color = yolo_core.color_for_class(detection.class_id)
        x1, y1, x2, y2 = detection.bbox_xyxy
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
        label = f'{detection.class_name} {detection.confidence:.2f}'
        text_box = draw.textbbox((0, 0), label, font=font)
        text_width = text_box[2] - text_box[0] + 8
        text_height = text_box[3] - text_box[1] + 6
        label_y = y1 - text_height if y1 >= text_height else y1
        draw.rectangle((x1, label_y, x1 + text_width, label_y + text_height), fill=color)
        luminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
        text_color = (0, 0, 0) if luminance > 150 else (255, 255, 255)
        draw.text((x1 + 4, label_y + 3), label, fill=text_color, font=font)
    if not detections_list:
        label = 'No COCO detections above threshold'
        box = draw.textbbox((0, 0), label, font=font)
        draw.rectangle((8, 8, box[2] - box[0] + 24, box[3] - box[1] + 20), fill=(20, 24, 31))
        draw.text((16, 14), label, fill=(255, 255, 255), font=font)
    return preview


def _save_crops(image: Image.Image, detections: list[Any], crops_dir: Path, item_id: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    source = image.convert('RGB')
    for index, detection in enumerate(detections):
        x1, y1, x2, y2 = detection.bbox_xyxy
        left = max(0, min(source.width - 1, int(math.floor(x1))))
        top = max(0, min(source.height - 1, int(math.floor(y1))))
        right = max(left + 1, min(source.width, int(math.ceil(x2))))
        bottom = max(top + 1, min(source.height, int(math.ceil(y2))))
        class_dir = crops_dir / str(detection.class_name).replace('/', '_')
        crop_path = class_dir / f'{item_id}-{index:04d}.jpg'
        class_dir.mkdir(parents=True, exist_ok=True)
        source.crop((left, top, right, bottom)).save(crop_path, 'JPEG', quality=90, optimize=True)
        output.append({
            'index': index,
            'class_name': detection.class_name,
            'confidence': round(float(detection.confidence), 6),
            'path': str(crop_path),
        })
    return output


def _result_record(
    *,
    request: dict[str, Any],
    item_id: str,
    source_path: Path,
    source_sha: str,
    source_type: str,
    source_image: Image.Image,
    detections: list[Any],
    annotated_path: Path,
    render: dict[str, Any],
    crops: list[dict[str, Any]],
    actual_model_sha: str,
    adapter: str,
    requested_provider: str,
    plan: dict[str, Any],
    session: Any,
    provider_fallback: bool,
    allow_provider_fallback: bool,
    device_id: int,
    coreml_compute_units: str,
    session_reused: bool,
    confidence: float,
    nms_iou: float,
    max_detections: int,
    inference_ms: float,
    frame_index: int | None = None,
    timestamp_seconds: float | None = None,
) -> dict[str, Any]:
    detection_payloads = [detection.as_dict() for detection in detections]
    crop_by_index = {item['index']: item['path'] for item in crops}
    for index, payload in enumerate(detection_payloads):
        if index in crop_by_index:
            payload['crop_path'] = crop_by_index[index]
    return {
        'schema_version': 7,
        'item_id': item_id,
        'source_path': str(source_path),
        'source_sha256': source_sha,
        'source_type': source_type,
        'source_width': source_image.width,
        'source_height': source_image.height,
        'frame_index': frame_index,
        'timestamp_seconds': timestamp_seconds,
        'model_id': request.get('model_id'),
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'requested_provider': requested_provider,
        'configured_providers': plan['provider_names'],
        'execution_providers': session.get_providers(),
        'provider_options': plan['provider_options'],
        'provider_fallback': provider_fallback,
        'allow_provider_fallback': allow_provider_fallback,
        'device_id': device_id,
        'coreml_compute_units': coreml_compute_units,
        'session_reused': session_reused,
        'inference_ms': round(inference_ms, 3),
        'thresholds': {'confidence': confidence, 'nms_iou': nms_iou, 'max_detections': max_detections},
        'detections': detection_payloads,
        'detection_count': len(detections),
        'classes': sorted({str(item['class_name']) for item in detection_payloads}),
        'annotated': {'path': str(annotated_path), **render},
        'crops': crops,
    }


def _write_exports(output_dir: Path, items: list[dict[str, Any]], labels: list[str]) -> dict[str, Any]:
    import json

    exports_dir = output_dir / 'exports'
    exports_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = exports_dir / 'detections.jsonl'
    csv_path = exports_dir / 'detections.csv'
    coco_path = exports_dir / 'coco.json'
    class_summary_path = exports_dir / 'class-summary.json'

    with jsonl_path.open('w', encoding='utf-8', newline='\n') as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n')

    with csv_path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow([
            'item_id', 'source_path', 'source_type', 'frame_index', 'timestamp_seconds',
            'class_id', 'class_name', 'confidence', 'x1', 'y1', 'x2', 'y2',
            'area_pixels', 'area_fraction', 'crop_path', 'annotated_path',
        ])
        for item in items:
            detections = item.get('detections') or []
            if not detections:
                writer.writerow([
                    item.get('item_id'), item.get('source_path'), item.get('source_type'),
                    item.get('frame_index'), item.get('timestamp_seconds'),
                    '', '', '', '', '', '', '', '', '', '',
                    (item.get('annotated') or {}).get('path'),
                ])
            for detection in detections:
                bbox = detection.get('bbox_xyxy') or ['', '', '', '']
                writer.writerow([
                    item.get('item_id'), item.get('source_path'), item.get('source_type'),
                    item.get('frame_index'), item.get('timestamp_seconds'),
                    detection.get('class_id'), detection.get('class_name'), detection.get('confidence'),
                    *bbox, detection.get('area_pixels'), detection.get('area_fraction'),
                    detection.get('crop_path', ''), (item.get('annotated') or {}).get('path'),
                ])

    coco_images = []
    coco_annotations = []
    annotation_id = 1
    for image_id, item in enumerate(items, 1):
        coco_images.append({
            'id': image_id,
            'file_name': item.get('source_path'),
            'width': item.get('source_width'),
            'height': item.get('source_height'),
            'frame_index': item.get('frame_index'),
            'timestamp_seconds': item.get('timestamp_seconds'),
        })
        for detection in item.get('detections') or []:
            x1, y1, x2, y2 = detection['bbox_xyxy']
            coco_annotations.append({
                'id': annotation_id,
                'image_id': image_id,
                'category_id': int(detection['class_id']) + 1,
                'bbox': [x1, y1, x2 - x1, y2 - y1],
                'area': detection.get('area_pixels'),
                'iscrowd': 0,
                'score': detection.get('confidence'),
                'crop_path': detection.get('crop_path'),
            })
            annotation_id += 1
    write_json(coco_path, {
        'info': {'description': 'Media Experiment Ledger detection export', 'schema_version': 1},
        'images': coco_images,
        'annotations': coco_annotations,
        'categories': [{'id': index + 1, 'name': name} for index, name in enumerate(labels)],
    })

    class_counts: dict[str, int] = {}
    for item in items:
        for detection in item.get('detections') or []:
            name = str(detection.get('class_name') or 'unknown')
            class_counts[name] = class_counts.get(name, 0) + 1
    write_json(class_summary_path, {
        'schema_version': 1,
        'items': len(items),
        'boxes': sum(class_counts.values()),
        'classes': [{'name': name, 'count': count} for name, count in sorted(class_counts.items())],
    })
    annotated_media = sorted({
        str((item.get('annotated') or {}).get('path'))
        for item in items
        if (item.get('annotated') or {}).get('path')
    })
    return {
        'jsonl': str(jsonl_path),
        'csv': str(csv_path),
        'coco_json': str(coco_path),
        'class_summary': str(class_summary_path),
        'annotated_media': annotated_media,
    }


def _mux_audio(source_path: Path, silent_video: Path, destination: Path) -> bool:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(silent_video), '-i', str(source_path),
        '-map', '0:v:0', '-map', '1:a?', '-c:v', 'copy', '-c:a', 'aac',
        '-shortest', '-movflags', '+faststart', str(destination),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=3600, check=False)
        return completed.returncode == 0 and destination.is_file() and destination.stat().st_size > 0
    except (OSError, subprocess.SubprocessError):
        return False


def _encode_annotated_video(
    source_path: Path,
    destination: Path,
    frame_cache: dict[int, Path],
    *,
    fps: float,
) -> dict[str, Any]:
    iterator = iio.imiter(source_path)
    first = next(iterator, None)
    if first is None:
        raise ValueError(f'Video contains no decodable frames: {source_path}')
    first_array = np.asarray(first, dtype=np.uint8)
    height, width = first_array.shape[:2]
    destination.parent.mkdir(parents=True, exist_ok=True)
    silent_path = destination.with_name(destination.stem + '.video-only.mp4')
    writer = imageio_ffmpeg.write_frames(
        str(silent_path),
        (width, height),
        fps=max(1.0, fps),
        codec='libx264',
        pix_fmt_in='rgb24',
        pix_fmt_out='yuv420p',
        output_params=['-movflags', '+faststart', '-preset', 'medium', '-crf', '20'],
        ffmpeg_log_level='error',
    )
    writer.send(None)

    def encoded_frame(index: int, frame: np.ndarray) -> bytes:
        cache_path = frame_cache.get(index)
        if cache_path and cache_path.is_file():
            with Image.open(cache_path) as cached:
                array = np.asarray(cached.convert('RGB').resize((width, height)), dtype=np.uint8)
        else:
            array = np.asarray(Image.fromarray(frame).convert('RGB'), dtype=np.uint8)
        return np.ascontiguousarray(array).tobytes()

    frame_count = 0
    try:
        writer.send(encoded_frame(0, first_array))
        frame_count = 1
        for index, frame in enumerate(iterator, 1):
            writer.send(encoded_frame(index, np.asarray(frame, dtype=np.uint8)))
            frame_count = index + 1
    finally:
        writer.close()

    audio_preserved = _mux_audio(source_path, silent_path, destination)
    if not audio_preserved:
        silent_path.replace(destination)
    else:
        silent_path.unlink(missing_ok=True)
    return {
        'path': str(destination),
        'fps': fps,
        'frame_count': frame_count,
        'width': width,
        'height': height,
        'audio_preserved': audio_preserved,
        'annotation_policy': 'sampled-frames-only',
    }


def run_detection(request: dict[str, Any]) -> dict[str, Any]:
    model_path, actual_model_sha, adapter, input_width, input_height = _verified_model(request)
    yolo_core, nanodet_core, labels_path = _load_vendor_modules()
    labels = yolo_core.load_labels(labels_path)

    try:
        import onnxruntime as ort
    except ImportError as error:
        raise RuntimeError('onnxruntime is required for detector inference') from error

    requested_provider = str(request.get('execution_provider', 'cpu')).lower()
    allow_provider_fallback = bool(request.get('allow_provider_fallback', True))
    device_id = int(request.get('device_id', 0))
    coreml_compute_units = str(request.get('coreml_compute_units') or 'ALL').upper()
    session, plan, input_meta, output_names, session_reused = _session_for(
        ort, model_path, actual_model_sha, requested_provider,
        allow_provider_fallback, device_id, coreml_compute_units,
    )

    files = iter_media([str(request.get('input_path', ''))])
    output_dir = Path(str(request.get('output_path') or '.')).resolve()
    annotations_dir = output_dir / 'annotated'
    sidecars_dir = output_dir / 'results'
    crops_dir = output_dir / 'crops'
    frame_cache_root = output_dir / '.annotated-frame-cache'
    for directory in (annotations_dir, sidecars_dir, crops_dir, frame_cache_root):
        directory.mkdir(parents=True, exist_ok=True)

    confidence = float(request.get('score_threshold', 0.35))
    nms_iou = float(request.get('nms_iou_threshold', 0.45))
    max_detections = int(request.get('max_detections', 300))
    export_crops = bool(request.get('export_crops', True))
    export_annotated_video = bool(request.get('export_annotated_video', True))
    every_n_frames = max(1, int(request.get('sample_every_n_frames', 1)))
    target_fps = max(0.0, float(request.get('sample_target_fps', 0.0)))
    max_sampled_frames = max(0, int(request.get('max_sampled_frames', 0)))
    provider_fallback = bool(plan['provider_fallback'])
    fingerprint = json_fingerprint({
        'schema': 7,
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'input_width': input_width,
        'input_height': input_height,
        'confidence': confidence,
        'nms_iou': nms_iou,
        'max_detections': max_detections,
        'requested_provider': requested_provider,
        'configured_providers': plan['provider_names'],
        'provider_options': plan['provider_options'],
        'provider_fallback': provider_fallback,
        'allow_provider_fallback': allow_provider_fallback,
        'device_id': device_id,
        'coreml_compute_units': coreml_compute_units,
        'sample_every_n_frames': every_n_frames,
        'sample_target_fps': target_fps,
        'max_sampled_frames': max_sampled_frames,
        'export_crops': export_crops,
        'export_annotated_video': export_annotated_video,
    })
    checkpoint_path = output_dir / '.mel-detection-checkpoint.json'
    checkpoint = read_json(checkpoint_path, {})
    completed: dict[str, Any] = checkpoint.get('completed', {}) if checkpoint.get('fingerprint') == fingerprint else {}
    results: list[dict[str, Any]] = []
    videos: list[dict[str, Any]] = []
    total_media = len(files)
    processed_media = 0

    for path in files:
        source_sha = sha256(path)
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            item_key = str(path)
            previous = completed.get(item_key)
            if previous and previous.get('source_sha256') == source_sha and Path(previous.get('sidecar', '')).is_file():
                results.append(read_json(Path(previous['sidecar']), previous))
                processed_media += 1
                emit('progress', stage='resuming image', progress=processed_media / max(total_media, 1) * 100, completed=processed_media, total=total_media)
                continue
            with Image.open(path) as image:
                detections, source_image, inference_ms = _infer_image(
                    image, adapter=adapter, input_width=input_width, input_height=input_height,
                    confidence=confidence, nms_iou=nms_iou, max_detections=max_detections,
                    session=session, input_meta=input_meta, output_names=output_names,
                    labels=labels, yolo_core=yolo_core, nanodet_core=nanodet_core,
                )
            item_id = json_fingerprint({'path': str(path), 'sha256': source_sha})[:20]
            annotated_path = annotations_dir / f'{item_id}.jpg'
            render = yolo_core.render_annotated(source_image, detections, annotated_path)
            crops = _save_crops(source_image, detections, crops_dir, item_id) if export_crops else []
            sidecar_path = sidecars_dir / f'{item_id}.json'
            result = _result_record(
                request=request, item_id=item_id, source_path=path, source_sha=source_sha,
                source_type='image', source_image=source_image, detections=detections,
                annotated_path=annotated_path, render=render, crops=crops,
                actual_model_sha=actual_model_sha, adapter=adapter, requested_provider=requested_provider,
                plan=plan, session=session, provider_fallback=provider_fallback,
                allow_provider_fallback=allow_provider_fallback, device_id=device_id,
                coreml_compute_units=coreml_compute_units, session_reused=session_reused,
                confidence=confidence, nms_iou=nms_iou, max_detections=max_detections,
                inference_ms=inference_ms,
            )
            write_json(sidecar_path, result)
            results.append(result)
            completed[item_key] = {'source_sha256': source_sha, 'sidecar': str(sidecar_path), 'annotated': str(annotated_path)}
            write_json(checkpoint_path, {'schema_version': 2, 'fingerprint': fingerprint, 'completed': completed})
            processed_media += 1
            emit('progress', stage='image inference', progress=processed_media / max(total_media, 1) * 100, completed=processed_media, total=total_media)
            continue

        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        metadata = _video_metadata(path)
        video_id = json_fingerprint({'path': str(path), 'sha256': source_sha})[:20]
        video_sidecars = sidecars_dir / video_id
        video_frame_cache = frame_cache_root / video_id
        video_sidecars.mkdir(parents=True, exist_ok=True)
        video_frame_cache.mkdir(parents=True, exist_ok=True)
        sampled_results: list[dict[str, Any]] = []
        frame_cache: dict[int, Path] = {}
        sampled_count = 0
        decoded_count = 0
        for frame_index, frame in enumerate(iio.imiter(path)):
            decoded_count = frame_index + 1
            if not should_sample_frame(
                frame_index,
                source_fps=float(metadata['fps']),
                every_n_frames=every_n_frames,
                target_fps=target_fps,
            ):
                continue
            if max_sampled_frames and sampled_count >= max_sampled_frames:
                break
            sampled_count += 1
            item_key = f'{path}#frame={frame_index}'
            sidecar_path = video_sidecars / f'{frame_index:012d}.json'
            annotated_path = video_frame_cache / f'{frame_index:012d}.jpg'
            previous = completed.get(item_key)
            if (
                previous
                and previous.get('source_sha256') == source_sha
                and Path(previous.get('sidecar', '')).is_file()
                and Path(previous.get('annotated', '')).is_file()
            ):
                result = read_json(Path(previous['sidecar']), previous)
                sampled_results.append(result)
                frame_cache[frame_index] = Path(previous['annotated'])
                emit('progress', stage='resuming video frames', progress=0, completed=sampled_count, total=max_sampled_frames or int(metadata['frame_count']) or 0)
                continue

            source_image = Image.fromarray(np.asarray(frame, dtype=np.uint8)).convert('RGB')
            detections, prepared_image, inference_ms = _infer_image(
                source_image, adapter=adapter, input_width=input_width, input_height=input_height,
                confidence=confidence, nms_iou=nms_iou, max_detections=max_detections,
                session=session, input_meta=input_meta, output_names=output_names,
                labels=labels, yolo_core=yolo_core, nanodet_core=nanodet_core,
            )
            annotated = _annotate_full_resolution(yolo_core, prepared_image, detections)
            annotated.save(annotated_path, 'JPEG', quality=88, optimize=True)
            item_id = f'{video_id}-{frame_index:012d}'
            crops = _save_crops(prepared_image, detections, crops_dir, item_id) if export_crops else []
            result = _result_record(
                request=request, item_id=item_id, source_path=path, source_sha=source_sha,
                source_type='video-frame', source_image=prepared_image, detections=detections,
                annotated_path=annotated_path,
                render={'width': prepared_image.width, 'height': prepared_image.height, 'scale': 1.0},
                crops=crops, actual_model_sha=actual_model_sha, adapter=adapter,
                requested_provider=requested_provider, plan=plan, session=session,
                provider_fallback=provider_fallback, allow_provider_fallback=allow_provider_fallback,
                device_id=device_id, coreml_compute_units=coreml_compute_units,
                session_reused=session_reused, confidence=confidence, nms_iou=nms_iou,
                max_detections=max_detections, inference_ms=inference_ms,
                frame_index=frame_index, timestamp_seconds=frame_index / float(metadata['fps']),
            )
            write_json(sidecar_path, result)
            sampled_results.append(result)
            frame_cache[frame_index] = annotated_path
            completed[item_key] = {'source_sha256': source_sha, 'sidecar': str(sidecar_path), 'annotated': str(annotated_path)}
            write_json(checkpoint_path, {'schema_version': 2, 'fingerprint': fingerprint, 'completed': completed})
            emit('progress', stage='video inference', progress=0, completed=sampled_count, total=max_sampled_frames or int(metadata['frame_count']) or 0)

        video_export = None
        if export_annotated_video and frame_cache:
            video_export = _encode_annotated_video(
                path,
                annotations_dir / f'{video_id}-annotated.mp4',
                frame_cache,
                fps=float(metadata['fps']),
            )
        videos.append({
            'source_path': str(path),
            'source_sha256': source_sha,
            'video_id': video_id,
            'metadata': {**metadata, 'decoded_frame_count': decoded_count},
            'sampling': {
                'every_n_frames': every_n_frames,
                'target_fps': target_fps,
                'sampled_frame_count': len(sampled_results),
                'max_sampled_frames': max_sampled_frames,
            },
            'annotated_video': video_export,
        })
        results.extend(sampled_results)
        processed_media += 1
        emit('progress', stage='video finalized', progress=processed_media / max(total_media, 1) * 100, completed=processed_media, total=total_media)

    exports = _write_exports(output_dir, results, labels)
    for video in videos:
        if video.get('annotated_video'):
            exports['annotated_media'].append(video['annotated_video']['path'])
    exports['annotated_media'] = sorted(set(exports['annotated_media']))
    manifest = {
        'schema_version': 7,
        'job_fingerprint': fingerprint,
        'model_id': request.get('model_id'),
        'model_path': str(model_path),
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'requested_provider': requested_provider,
        'configured_providers': plan['provider_names'],
        'execution_providers': session.get_providers(),
        'provider_options': plan['provider_options'],
        'provider_fallback': provider_fallback,
        'allow_provider_fallback': allow_provider_fallback,
        'device_id': device_id,
        'coreml_compute_units': coreml_compute_units,
        'session_reused': session_reused,
        'input_count': len(files),
        'image_count': sum(1 for path in files if path.suffix.lower() in IMAGE_EXTENSIONS),
        'video_count': len(videos),
        'sampled_item_count': len(results),
        'detected_item_count': sum(1 for item in results if item.get('detection_count', 0) > 0),
        'box_count': sum(int(item.get('detection_count', 0)) for item in results),
        'class_names': sorted({name for item in results for name in item.get('classes', [])}),
        'sampling': {
            'every_n_frames': every_n_frames,
            'target_fps': target_fps,
            'max_sampled_frames': max_sampled_frames,
        },
        'videos': videos,
        'items': results,
        'exports': exports,
        'accuracy_claim': None,
    }
    manifest_path = output_dir / 'detection-manifest.json'
    write_json(manifest_path, manifest)
    manifest['manifest_path'] = str(manifest_path)
    return manifest


def _benchmark_inputs(input_path: str, limit: int) -> list[Image.Image]:
    images: list[Image.Image] = []
    for path in iter_media([input_path]):
        if len(images) >= limit:
            break
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            with Image.open(path) as image:
                images.append(image.convert('RGB').copy())
        elif path.suffix.lower() in VIDEO_EXTENSIONS:
            for frame in iio.imiter(path):
                images.append(Image.fromarray(np.asarray(frame, dtype=np.uint8)).convert('RGB'))
                break
    if not images:
        raise ValueError('Benchmark input must contain at least one decodable image or video frame.')
    return images


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def run_detection_benchmark(request: dict[str, Any]) -> dict[str, Any]:
    model_path, actual_model_sha, adapter, input_width, input_height = _verified_model(request)
    yolo_core, nanodet_core, labels_path = _load_vendor_modules()
    labels = yolo_core.load_labels(labels_path)
    sample_count = max(1, min(64, int(request.get('benchmark_sample_count', 4))))
    warm_iterations = max(1, min(200, int(request.get('warm_iterations', 10))))
    inputs = _benchmark_inputs(str(request.get('input_path') or ''), sample_count)

    try:
        import onnxruntime as ort
    except ImportError as error:
        raise RuntimeError('onnxruntime is required for detector inference') from error

    requested_provider = str(request.get('execution_provider', 'cpu')).lower()
    allow_provider_fallback = bool(request.get('allow_provider_fallback', True))
    device_id = int(request.get('device_id', 0))
    coreml_compute_units = str(request.get('coreml_compute_units') or 'ALL').upper()
    confidence = float(request.get('score_threshold', 0.35))
    nms_iou = float(request.get('nms_iou_threshold', 0.45))
    max_detections = int(request.get('max_detections', 300))

    clear_detection_session_cache()
    cold_started = time.perf_counter()
    session, plan, input_meta, output_names, cold_reused = _session_for(
        ort, model_path, actual_model_sha, requested_provider,
        allow_provider_fallback, device_id, coreml_compute_units,
    )
    detections, _, cold_inference_ms = _infer_image(
        inputs[0], adapter=adapter, input_width=input_width, input_height=input_height,
        confidence=confidence, nms_iou=nms_iou, max_detections=max_detections,
        session=session, input_meta=input_meta, output_names=output_names,
        labels=labels, yolo_core=yolo_core, nanodet_core=nanodet_core,
    )
    cold_total_ms = (time.perf_counter() - cold_started) * 1000.0
    steady_ms: list[float] = []
    steady_box_counts: list[int] = []
    for iteration in range(warm_iterations):
        image = inputs[iteration % len(inputs)]
        started = time.perf_counter()
        warm_detections, _, _ = _infer_image(
            image, adapter=adapter, input_width=input_width, input_height=input_height,
            confidence=confidence, nms_iou=nms_iou, max_detections=max_detections,
            session=session, input_meta=input_meta, output_names=output_names,
            labels=labels, yolo_core=yolo_core, nanodet_core=nanodet_core,
        )
        steady_ms.append((time.perf_counter() - started) * 1000.0)
        steady_box_counts.append(len(warm_detections))
        emit('progress', stage='benchmark steady-state', progress=(iteration + 1) / warm_iterations * 100, completed=iteration + 1, total=warm_iterations)

    median_ms = statistics.median(steady_ms)
    output_dir = Path(str(request.get('output_path') or '.')).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        'schema_version': 1,
        'suite_id': request.get('benchmark_suite_id'),
        'model_id': request.get('model_id'),
        'model_path': str(model_path),
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'input_width': input_width,
        'input_height': input_height,
        'requested_provider': requested_provider,
        'configured_providers': plan['provider_names'],
        'execution_providers': session.get_providers(),
        'provider_options': plan['provider_options'],
        'provider_fallback': bool(plan['provider_fallback']),
        'allow_provider_fallback': allow_provider_fallback,
        'device_id': device_id,
        'coreml_compute_units': coreml_compute_units,
        'cold': {
            'session_reused': cold_reused,
            'session_and_first_inference_ms': round(cold_total_ms, 3),
            'first_inference_ms': round(cold_inference_ms, 3),
            'session_initialization_ms': round(max(0.0, cold_total_ms - cold_inference_ms), 3),
            'box_count': len(detections),
        },
        'steady_state': {
            'iterations': warm_iterations,
            'sample_count': len(inputs),
            'median_ms': round(median_ms, 3),
            'p95_ms': round(_percentile(steady_ms, 95), 3),
            'minimum_ms': round(min(steady_ms), 3),
            'maximum_ms': round(max(steady_ms), 3),
            'throughput_items_per_second': round(1000.0 / median_ms, 3) if median_ms > 0 else 0.0,
            'box_counts': steady_box_counts,
        },
        'accuracy_claim': None,
    }
    manifest_path = output_dir / 'benchmark-manifest.json'
    write_json(manifest_path, result)
    result['manifest_path'] = str(manifest_path)
    return result
