from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from tools.yolo_core import (
    Detection,
    nms,
    postprocess_predictions,
    prepare_image,
    render_annotated,
)


class YoloCoreTests(unittest.TestCase):
    def test_letterbox_preserves_aspect_ratio(self) -> None:
        image = Image.new("RGB", (800, 400), "white")
        result = prepare_image(image, (416, 416))
        self.assertEqual(result.tensor.shape, (1, 3, 416, 416))
        self.assertAlmostEqual(result.scale, 0.52)
        self.assertEqual((result.pad_left, result.pad_top), (0, 0))

    def test_class_aware_nms(self) -> None:
        boxes = np.array(
            [[0, 0, 100, 100], [5, 5, 98, 98], [200, 200, 250, 250]],
            dtype=np.float32,
        )
        scores = np.array([0.9, 0.8, 0.7], dtype=np.float32)
        self.assertEqual(nms(boxes, scores, 0.5), [0, 2])

    def test_postprocess_synthetic_detection_maps_to_original(self) -> None:
        image = Image.new("RGB", (416, 416), "white")
        letterbox = prepare_image(image, (416, 416))
        rows = sum((416 // stride) * (416 // stride) for stride in (8, 16, 32))
        raw = np.zeros((1, rows, 85), dtype=np.float32)
        raw[0, 0, 4] = 0.95
        raw[0, 0, 5] = 0.95
        detections = postprocess_predictions(
            raw,
            letterbox,
            [f"class-{index}" for index in range(80)],
            confidence_threshold=0.25,
            nms_iou_threshold=0.45,
            max_detections=100,
            input_size=(416, 416),
        )
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].class_id, 0)
        self.assertGreater(detections[0].confidence, 0.9)

    def test_render_is_decodable_with_and_without_boxes(self) -> None:
        detection = Detection(
            0,
            "person",
            0.9,
            (10, 10, 80, 90),
            (0.1, 0.1, 0.8, 0.9),
            5600,
            0.56,
        )
        with tempfile.TemporaryDirectory() as temp:
            for name, detections in (("boxed.jpg", [detection]), ("empty.jpg", [])):
                path = Path(temp) / name
                render_annotated(
                    Image.new("RGB", (100, 100), "white"), detections, path
                )
                with Image.open(path) as image:
                    image.load()
                    self.assertEqual(image.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
