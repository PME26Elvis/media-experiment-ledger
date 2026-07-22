from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .common import IMAGE_EXTENSIONS, emit, iter_media, json_fingerprint, read_json, sha256, write_json


def _load_vendor_modules():
    engine_root = Path(__file__).resolve().parents[1]
    packaged_vendor = engine_root / 'vendor'
    if packaged_vendor.is_dir():
        vendor = packaged_vendor
        labels_path = vendor / 'coco-80.json'
    else:
        repository_root = Path(__file__).resolve().parents[3]
        vendor = repository_root / 'tools'
        labels_path = repository_root / 'object-detection' / 'coco-80.json'
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    import yolo_core  # type: ignore
    import nanodet_core  # type: ignore
    return yolo_core, nanodet_core, labels_path


def select_providers(requested: str, available: list[str]) -> tuple[list[str], bool]:
    provider_map = {
        'cpu': 'CPUExecutionProvider',
        'cuda': 'CUDAExecutionProvider',
        'directml': 'DmlExecutionProvider',
        'coreml': 'CoreMLExecutionProvider',
    }
    desired = provider_map.get(requested.lower(), 'CPUExecutionProvider')
    if desired in available:
        return [desired], False
    if 'CPUExecutionProvider' not in available:
        raise RuntimeError(f'Neither requested provider {desired} nor CPU fallback is available: {available}')
    return ['CPUExecutionProvider'], desired != 'CPUExecutionProvider'


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


def run_detection(request: dict[str, Any]) -> dict[str, Any]:
    model_path = Path(str(request.get('model_path') or '')).expanduser().resolve()
    if not model_path.is_file():
        raise ValueError('A verified ONNX model_path is required. Model Manager must import the selected model first.')
    actual_model_sha = sha256(model_path)
    expected_model_sha = str(request.get('model_sha256') or '').lower()
    if expected_model_sha and actual_model_sha != expected_model_sha:
        raise ValueError(f'model SHA-256 changed after import: expected {expected_model_sha}, got {actual_model_sha}')

    yolo_core, nanodet_core, labels_path = _load_vendor_modules()
    labels = yolo_core.load_labels(labels_path)
    adapter = str(request.get('adapter') or '')
    input_width = int(request.get('input_width') or 0)
    input_height = int(request.get('input_height') or 0)
    if input_width <= 0 or input_height <= 0:
        raise ValueError('model registry input_width and input_height are required')

    try:
        import onnxruntime as ort
    except ImportError as error:
        raise RuntimeError('onnxruntime is required for detector inference') from error
    providers, provider_fallback = select_providers(str(request.get('execution_provider', 'cpu')), ort.get_available_providers())
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(model_path), options, providers=providers)
    input_meta = session.get_inputs()[0]
    output_names = [item.name for item in session.get_outputs()]

    files = [path for path in iter_media([str(request.get('input_path', ''))]) if path.suffix.lower() in IMAGE_EXTENSIONS]
    output_dir = Path(str(request.get('output_path') or '.')).resolve()
    annotations_dir = output_dir / 'annotated'
    sidecars_dir = output_dir / 'results'
    annotations_dir.mkdir(parents=True, exist_ok=True)
    sidecars_dir.mkdir(parents=True, exist_ok=True)

    confidence = float(request.get('score_threshold', 0.35))
    nms_iou = float(request.get('nms_iou_threshold', 0.45))
    max_detections = int(request.get('max_detections', 300))
    fingerprint = json_fingerprint({
        'schema': 2,
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'input_width': input_width,
        'input_height': input_height,
        'confidence': confidence,
        'nms_iou': nms_iou,
        'max_detections': max_detections,
        'providers': session.get_providers(),
    })
    checkpoint_path = output_dir / '.mel-detection-checkpoint.json'
    checkpoint = read_json(checkpoint_path, {})
    completed: dict[str, Any] = checkpoint.get('completed', {}) if checkpoint.get('fingerprint') == fingerprint else {}
    results: list[dict[str, Any]] = []

    for index, path in enumerate(files, 1):
        source_sha = sha256(path)
        previous = completed.get(str(path))
        if previous and previous.get('source_sha256') == source_sha and Path(previous.get('sidecar', '')).is_file():
            results.append(read_json(Path(previous['sidecar']), previous))
            emit('progress', stage='resuming', progress=index / max(len(files), 1) * 100, completed=index, total=len(files))
            continue

        with Image.open(path) as image:
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
            elif adapter == 'nanodet-plus-coco-v1':
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
            else:
                raise ValueError(f'unsupported detector adapter: {adapter}')

        item_id = json_fingerprint({'path': str(path), 'sha256': source_sha})[:20]
        annotated_path = annotations_dir / f'{item_id}.jpg'
        render = yolo_core.render_annotated(source_image, detections, annotated_path)
        sidecar_path = sidecars_dir / f'{item_id}.json'
        result = {
            'schema_version': 2,
            'item_id': item_id,
            'source_path': str(path),
            'source_sha256': source_sha,
            'model_id': request.get('model_id'),
            'model_sha256': actual_model_sha,
            'adapter': adapter,
            'execution_providers': session.get_providers(),
            'provider_fallback': provider_fallback,
            'thresholds': {'confidence': confidence, 'nms_iou': nms_iou, 'max_detections': max_detections},
            'detections': [detection.as_dict() for detection in detections],
            'detection_count': len(detections),
            'annotated': render,
        }
        write_json(sidecar_path, result)
        results.append(result)
        completed[str(path)] = {'source_sha256': source_sha, 'sidecar': str(sidecar_path), 'annotated': str(annotated_path)}
        write_json(checkpoint_path, {'schema_version': 1, 'fingerprint': fingerprint, 'completed': completed})
        emit('progress', stage='inference', progress=index / max(len(files), 1) * 100, completed=index, total=len(files))

    manifest = {
        'schema_version': 2,
        'job_fingerprint': fingerprint,
        'model_id': request.get('model_id'),
        'model_path': str(model_path),
        'model_sha256': actual_model_sha,
        'adapter': adapter,
        'requested_provider': request.get('execution_provider', 'cpu'),
        'execution_providers': session.get_providers(),
        'provider_fallback': provider_fallback,
        'input_count': len(files),
        'detected_item_count': sum(1 for item in results if item.get('detection_count', 0) > 0),
        'box_count': sum(int(item.get('detection_count', 0)) for item in results),
        'items': results,
        'accuracy_claim': None,
    }
    write_json(output_dir / 'detection-manifest.json', manifest)
    return manifest
