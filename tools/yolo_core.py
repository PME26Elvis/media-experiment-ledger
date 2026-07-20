"""Deterministic YOLOX-Tiny ONNX inference and rendering primitives."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class LetterboxResult:
    tensor: np.ndarray
    image: Image.Image
    scale: float
    pad_left: int
    pad_top: int
    original_width: int
    original_height: int


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    bbox_normalized_xyxy: tuple[float, float, float, float]
    area_pixels: float
    area_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 6),
            "bbox_xyxy": [round(value, 6) for value in self.bbox_xyxy],
            "bbox_normalized_xyxy": [
                round(value, 6) for value in self.bbox_normalized_xyxy
            ],
            "area_pixels": round(self.area_pixels, 6),
            "area_fraction": round(self.area_fraction, 6),
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_labels(path: Path) -> list[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"COCO labels must be a non-empty string list: {path}")
    return [item.strip() for item in value]


def load_model_lock(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Model lock must be an object: {path}")
    required = {
        "model_family",
        "download_url",
        "sha256",
        "input_width",
        "input_height",
        "labels_path",
        "labels_sha256",
    }
    missing = sorted(required.difference(value))
    if missing:
        raise ValueError(f"Model lock missing fields: {', '.join(missing)}")
    if len(str(value["sha256"])) != 64 or len(str(value["labels_sha256"])) != 64:
        raise ValueError("Model and labels SHA-256 values must be 64 hex characters")
    return value


def verify_model_and_labels(model_path: Path, lock: dict[str, Any], labels_path: Path) -> None:
    actual_model = sha256_file(model_path)
    expected_model = str(lock["sha256"]).lower()
    if actual_model != expected_model:
        raise ValueError(f"Model SHA-256 mismatch: expected {expected_model}, got {actual_model}")
    expected_size = int(lock.get("expected_size_bytes") or 0)
    if expected_size and model_path.stat().st_size != expected_size:
        raise ValueError(
            f"Model size mismatch: expected {expected_size}, got {model_path.stat().st_size}"
        )
    actual_labels = sha256_file(labels_path)
    expected_labels = str(lock["labels_sha256"]).lower()
    if actual_labels != expected_labels:
        raise ValueError(
            f"Labels SHA-256 mismatch: expected {expected_labels}, got {actual_labels}"
        )


def prepare_image(image: Image.Image, input_size: tuple[int, int]) -> LetterboxResult:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"}:
        alpha = image.getchannel("A")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGB"), mask=alpha)
        image = background
    else:
        image = image.convert("RGB")
    original_width, original_height = image.size
    input_height, input_width = input_size
    scale = min(input_width / original_width, input_height / original_height)
    resized_width = max(1, int(original_width * scale))
    resized_height = max(1, int(original_height * scale))
    resized = image.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (input_width, input_height), (114, 114, 114))
    # YOLOX official preprocessing anchors the resized image at top-left.
    pad_left = 0
    pad_top = 0
    canvas.paste(resized, (pad_left, pad_top))
    array = np.asarray(canvas, dtype=np.float32)
    tensor = np.transpose(array, (2, 0, 1))[None, ...]
    return LetterboxResult(
        tensor=tensor,
        image=image,
        scale=scale,
        pad_left=pad_left,
        pad_top=pad_top,
        original_width=original_width,
        original_height=original_height,
    )


def demo_postprocess(outputs: np.ndarray, input_size: tuple[int, int]) -> np.ndarray:
    if outputs.ndim == 2:
        outputs = outputs[None, ...]
    if outputs.ndim != 3 or outputs.shape[-1] < 6:
        raise ValueError(f"Unexpected YOLOX output shape: {outputs.shape}")
    input_height, input_width = input_size
    grids: list[np.ndarray] = []
    expanded_strides: list[np.ndarray] = []
    for stride in (8, 16, 32):
        height = input_height // stride
        width = input_width // stride
        yv, xv = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
        grid = np.stack((xv, yv), axis=2).reshape(1, -1, 2)
        grids.append(grid)
        expanded_strides.append(np.full((*grid.shape[:2], 1), stride))
    grid = np.concatenate(grids, axis=1).astype(outputs.dtype)
    strides = np.concatenate(expanded_strides, axis=1).astype(outputs.dtype)
    if outputs.shape[1] != grid.shape[1]:
        return outputs.copy()
    decoded = outputs.copy()
    decoded[..., :2] = (decoded[..., :2] + grid) * strides
    decoded[..., 2:4] = np.exp(np.clip(decoded[..., 2:4], -20, 20)) * strides
    return decoded


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    top_left = np.maximum(box[:2], boxes[:, :2])
    bottom_right = np.minimum(box[2:], boxes[:, 2:])
    wh = np.maximum(0.0, bottom_right - top_left)
    intersection = wh[:, 0] * wh[:, 1]
    area_box = max(0.0, float((box[2] - box[0]) * (box[3] - box[1])))
    areas = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(
        0.0, boxes[:, 3] - boxes[:, 1]
    )
    union = area_box + areas - intersection
    return np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    if not len(boxes):
        return []
    order = np.argsort(-scores, kind="mergesort")
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        remaining = order[1:]
        overlaps = _iou(boxes[current], boxes[remaining])
        order = remaining[overlaps <= iou_threshold]
    return keep


def postprocess_predictions(
    raw_output: np.ndarray,
    letterbox: LetterboxResult,
    labels: Sequence[str],
    *,
    confidence_threshold: float,
    nms_iou_threshold: float,
    max_detections: int,
    input_size: tuple[int, int],
) -> list[Detection]:
    decoded = demo_postprocess(np.asarray(raw_output), input_size)[0]
    boxes_xywh = decoded[:, :4]
    objectness = decoded[:, 4:5]
    class_probs = decoded[:, 5:]
    if class_probs.shape[1] != len(labels):
        raise ValueError(
            f"Model output class count {class_probs.shape[1]} does not match labels {len(labels)}"
        )
    class_ids = np.argmax(class_probs, axis=1)
    class_scores = class_probs[np.arange(class_probs.shape[0]), class_ids]
    scores = objectness[:, 0] * class_scores
    selected = np.where(scores >= confidence_threshold)[0]
    if not selected.size:
        return []

    boxes = np.empty((len(selected), 4), dtype=np.float32)
    chosen = boxes_xywh[selected]
    boxes[:, 0] = chosen[:, 0] - chosen[:, 2] / 2
    boxes[:, 1] = chosen[:, 1] - chosen[:, 3] / 2
    boxes[:, 2] = chosen[:, 0] + chosen[:, 2] / 2
    boxes[:, 3] = chosen[:, 1] + chosen[:, 3] / 2
    selected_scores = scores[selected]
    selected_classes = class_ids[selected]

    keep_global: list[int] = []
    for class_id in sorted(set(int(value) for value in selected_classes.tolist())):
        class_positions = np.where(selected_classes == class_id)[0]
        kept = nms(boxes[class_positions], selected_scores[class_positions], nms_iou_threshold)
        keep_global.extend(int(class_positions[index]) for index in kept)
    keep_global.sort(
        key=lambda index: (
            -float(selected_scores[index]),
            int(selected_classes[index]),
            *[float(value) for value in boxes[index]],
        )
    )
    keep_global = keep_global[:max_detections]

    output: list[Detection] = []
    image_area = float(letterbox.original_width * letterbox.original_height)
    for position in keep_global:
        box = boxes[position].astype(float)
        box[[0, 2]] = (box[[0, 2]] - letterbox.pad_left) / letterbox.scale
        box[[1, 3]] = (box[[1, 3]] - letterbox.pad_top) / letterbox.scale
        box[0] = min(max(box[0], 0.0), float(letterbox.original_width))
        box[2] = min(max(box[2], 0.0), float(letterbox.original_width))
        box[1] = min(max(box[1], 0.0), float(letterbox.original_height))
        box[3] = min(max(box[3], 0.0), float(letterbox.original_height))
        width = max(0.0, box[2] - box[0])
        height = max(0.0, box[3] - box[1])
        if width <= 0 or height <= 0:
            continue
        area = width * height
        class_id = int(selected_classes[position])
        normalized = (
            box[0] / letterbox.original_width,
            box[1] / letterbox.original_height,
            box[2] / letterbox.original_width,
            box[3] / letterbox.original_height,
        )
        output.append(
            Detection(
                class_id=class_id,
                class_name=labels[class_id],
                confidence=float(selected_scores[position]),
                bbox_xyxy=tuple(float(value) for value in box),
                bbox_normalized_xyxy=normalized,
                area_pixels=area,
                area_fraction=area / image_area if image_area else 0.0,
            )
        )
    return output


def color_for_class(class_id: int) -> tuple[int, int, int]:
    hue = (class_id * 137.508) % 360
    chroma = 0.72
    lightness = 0.56
    c = (1 - abs(2 * lightness - 1)) * chroma
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = lightness - c / 2
    if hue < 60:
        rgb = (c, x, 0)
    elif hue < 120:
        rgb = (x, c, 0)
    elif hue < 180:
        rgb = (0, c, x)
    elif hue < 240:
        rgb = (0, x, c)
    elif hue < 300:
        rgb = (x, 0, c)
    else:
        rgb = (c, 0, x)
    return tuple(int((value + m) * 255) for value in rgb)


def render_annotated(
    image: Image.Image,
    detections: Sequence[Detection],
    destination: Path,
    *,
    max_edge: int = 1600,
    quality: int = 88,
) -> dict[str, Any]:
    source = ImageOps.exif_transpose(image).convert("RGB")
    scale = min(1.0, max_edge / max(source.size))
    if scale < 1:
        preview = source.resize(
            (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
            Image.Resampling.LANCZOS,
        )
    else:
        preview = source.copy()
    draw = ImageDraw.Draw(preview)
    font = ImageFont.load_default()
    line_width = max(2, round(min(preview.size) / 220))
    for detection in detections:
        color = color_for_class(detection.class_id)
        x1, y1, x2, y2 = (value * scale for value in detection.bbox_xyxy)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
        label = f"{detection.class_name} {detection.confidence:.2f}"
        text_box = draw.textbbox((0, 0), label, font=font, stroke_width=0)
        text_width = text_box[2] - text_box[0] + 8
        text_height = text_box[3] - text_box[1] + 6
        label_y = y1 - text_height if y1 >= text_height else y1
        draw.rectangle((x1, label_y, x1 + text_width, label_y + text_height), fill=color)
        luminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
        text_color = (0, 0, 0) if luminance > 150 else (255, 255, 255)
        draw.text((x1 + 4, label_y + 3), label, fill=text_color, font=font)
    if not detections:
        label = "No COCO detections above threshold"
        box = draw.textbbox((0, 0), label, font=font)
        width = box[2] - box[0] + 16
        height = box[3] - box[1] + 12
        draw.rectangle((8, 8, 8 + width, 8 + height), fill=(20, 24, 31))
        draw.text((16, 14), label, fill=(255, 255, 255), font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    preview.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)
    return {"width": preview.width, "height": preview.height, "scale": scale}


class YoloXSession:
    def __init__(self, model_path: Path, *, threads: int | None = None) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("onnxruntime is required for YOLO inference") from exc
        options = ort.SessionOptions()
        if threads:
            options.intra_op_num_threads = max(1, threads)
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [item.name for item in self.session.get_outputs()]

    def infer(self, tensor: np.ndarray) -> tuple[np.ndarray, float]:
        started = time.perf_counter()
        outputs = self.session.run(self.output_names, {self.input_name: tensor})
        elapsed = time.perf_counter() - started
        if not outputs:
            raise RuntimeError("ONNX model returned no outputs")
        return np.asarray(outputs[0]), elapsed
