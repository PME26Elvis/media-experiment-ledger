"""Deterministic NanoDet-Plus-m-320 ONNX preprocessing and postprocessing."""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageOps

from yolo_core import Detection, nms


@dataclass(frozen=True)
class NanoDetInput:
    tensor: np.ndarray
    image: Image.Image
    original_width: int
    original_height: int
    input_width: int
    input_height: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"NanoDet model lock must be an object: {path}")
    required = {
        "detector_id", "model_family", "upstream_tag", "checkpoint_url",
        "checkpoint_sha256", "input_width", "input_height", "strides",
        "reg_max", "labels_path", "labels_sha256", "preprocess",
    }
    missing = sorted(required.difference(value))
    if missing:
        raise ValueError(f"NanoDet model lock missing: {', '.join(missing)}")
    if len(str(value["checkpoint_sha256"])) != 64:
        raise ValueError("NanoDet checkpoint SHA-256 must contain 64 hex characters")
    return value


def verify_checkpoint(path: Path, lock: dict[str, Any], *, allow_unpinned: bool = False) -> str:
    actual = sha256_file(path)
    expected = str(lock["checkpoint_sha256"]).lower()
    if expected == "0" * 64 and allow_unpinned:
        return actual
    if actual != expected:
        raise ValueError(f"NanoDet checkpoint SHA-256 mismatch: expected {expected}, got {actual}")
    expected_size = int(lock.get("expected_checkpoint_size_bytes") or 0)
    if expected_size and path.stat().st_size != expected_size:
        raise ValueError(
            f"NanoDet checkpoint size mismatch: expected {expected_size}, got {path.stat().st_size}"
        )
    return actual


def verify_labels(path: Path, lock: dict[str, Any]) -> None:
    actual = sha256_file(path)
    expected = str(lock["labels_sha256"]).lower()
    if actual != expected:
        raise ValueError(f"COCO labels SHA-256 mismatch: expected {expected}, got {actual}")


def prepare_image(image: Image.Image, lock: dict[str, Any]) -> NanoDetInput:
    source = ImageOps.exif_transpose(image).convert("RGB")
    input_width = int(lock["input_width"])
    input_height = int(lock["input_height"])
    # Official NanoDet val pipeline uses OpenCV BGR, keep_ratio=False and a
    # direct 320x320 warp before channel-wise normalization.
    resized = source.resize((input_width, input_height), Image.Resampling.BILINEAR)
    rgb = np.asarray(resized, dtype=np.float32)
    bgr = rgb[..., ::-1].copy()
    preprocess = dict(lock["preprocess"])
    mean = np.asarray(preprocess["mean"], dtype=np.float32)
    std = np.asarray(preprocess["std"], dtype=np.float32)
    normalized = (bgr - mean) / std
    tensor = np.transpose(normalized, (2, 0, 1))[None, ...].astype(np.float32)
    return NanoDetInput(
        tensor=tensor,
        image=source,
        original_width=source.width,
        original_height=source.height,
        input_width=input_width,
        input_height=input_height,
    )


def _softmax(values: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = values - np.max(values, axis=axis, keepdims=True)
    exp = np.exp(np.clip(shifted, -80, 80))
    return exp / np.sum(exp, axis=axis, keepdims=True)


def center_priors(input_height: int, input_width: int, strides: Sequence[int]) -> np.ndarray:
    rows: list[np.ndarray] = []
    for stride in strides:
        height = math.ceil(input_height / stride)
        width = math.ceil(input_width / stride)
        y, x = np.meshgrid(
            np.arange(height, dtype=np.float32) * stride,
            np.arange(width, dtype=np.float32) * stride,
            indexing="ij",
        )
        flat_x = x.reshape(-1)
        flat_y = y.reshape(-1)
        flat_stride = np.full(flat_x.shape, float(stride), dtype=np.float32)
        rows.append(np.stack([flat_x, flat_y, flat_stride, flat_stride], axis=1))
    return np.concatenate(rows, axis=0)


def postprocess_predictions(
    raw_output: np.ndarray,
    prepared: NanoDetInput,
    labels: Sequence[str],
    lock: dict[str, Any],
    *,
    confidence_threshold: float,
    nms_iou_threshold: float,
    max_detections: int,
) -> list[Detection]:
    output = np.asarray(raw_output)
    if output.ndim == 3:
        output = output[0]
    reg_max = int(lock["reg_max"])
    expected_channels = len(labels) + 4 * (reg_max + 1)
    if output.ndim != 2 or output.shape[1] != expected_channels:
        raise ValueError(
            f"Unexpected NanoDet output shape {output.shape}; expected [N,{expected_channels}]"
        )
    priors = center_priors(
        prepared.input_height, prepared.input_width, [int(v) for v in lock["strides"]]
    )
    if output.shape[0] != priors.shape[0]:
        raise ValueError(
            f"NanoDet point count mismatch: model={output.shape[0]}, priors={priors.shape[0]}"
        )
    class_scores = output[:, : len(labels)]
    distributions = output[:, len(labels):].reshape(-1, 4, reg_max + 1)
    probabilities = _softmax(distributions)
    project = np.arange(reg_max + 1, dtype=np.float32)
    distances = np.sum(probabilities * project, axis=2) * priors[:, 2:3]
    boxes = np.empty((len(priors), 4), dtype=np.float32)
    boxes[:, 0] = priors[:, 0] - distances[:, 0]
    boxes[:, 1] = priors[:, 1] - distances[:, 1]
    boxes[:, 2] = priors[:, 0] + distances[:, 2]
    boxes[:, 3] = priors[:, 1] + distances[:, 3]
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, prepared.input_width)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, prepared.input_height)

    selected_rows, selected_classes, selected_scores = [], [], []
    for class_id in range(len(labels)):
        scores = class_scores[:, class_id]
        candidates = np.where(scores >= confidence_threshold)[0]
        if not candidates.size:
            continue
        kept = nms(boxes[candidates], scores[candidates], nms_iou_threshold)
        for local_index in kept:
            row = int(candidates[local_index])
            selected_rows.append(row)
            selected_classes.append(class_id)
            selected_scores.append(float(scores[row]))
    order = sorted(
        range(len(selected_rows)),
        key=lambda index: (
            -selected_scores[index], selected_classes[index], selected_rows[index]
        ),
    )[:max_detections]

    scale_x = prepared.original_width / prepared.input_width
    scale_y = prepared.original_height / prepared.input_height
    image_area = float(prepared.original_width * prepared.original_height)
    detections: list[Detection] = []
    for index in order:
        row = selected_rows[index]
        class_id = selected_classes[index]
        box = boxes[row].astype(float)
        box[[0, 2]] *= scale_x
        box[[1, 3]] *= scale_y
        width = max(0.0, box[2] - box[0])
        height = max(0.0, box[3] - box[1])
        if width <= 0 or height <= 0:
            continue
        area = width * height
        detections.append(
            Detection(
                class_id=class_id,
                class_name=labels[class_id],
                confidence=selected_scores[index],
                bbox_xyxy=tuple(float(v) for v in box),
                bbox_normalized_xyxy=(
                    box[0] / prepared.original_width,
                    box[1] / prepared.original_height,
                    box[2] / prepared.original_width,
                    box[3] / prepared.original_height,
                ),
                area_pixels=area,
                area_fraction=area / image_area if image_area else 0.0,
            )
        )
    return detections


class NanoDetSession:
    def __init__(self, model_path: Path, *, threads: int | None = None) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("onnxruntime is required for NanoDet inference") from exc
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
            raise RuntimeError("NanoDet ONNX model returned no outputs")
        return np.asarray(outputs[0]), elapsed
