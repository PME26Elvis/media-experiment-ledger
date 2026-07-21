from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from tools.nanodet_core import center_priors, postprocess_predictions, prepare_image


LOCK = {
    "input_width": 320,
    "input_height": 320,
    "strides": [8, 16, 32, 64],
    "reg_max": 7,
    "preprocess": {
        "color_order": "BGR",
        "keep_ratio": False,
        "mean": [103.53, 116.28, 123.675],
        "std": [57.375, 57.12, 58.395],
    },
}
LABELS = [f"class-{index}" for index in range(80)]


class NanoDetCoreTests(unittest.TestCase):
    def test_preprocess_uses_direct_bgr_resize_and_normalization(self) -> None:
        image = Image.new("RGB", (640, 320), (255, 0, 0))
        prepared = prepare_image(image, LOCK)
        self.assertEqual(prepared.tensor.shape, (1, 3, 320, 320))
        self.assertEqual((prepared.original_width, prepared.original_height), (640, 320))
        expected_b = (0.0 - 103.53) / 57.375
        expected_g = (0.0 - 116.28) / 57.12
        expected_r = (255.0 - 123.675) / 58.395
        self.assertAlmostEqual(float(prepared.tensor[0, 0, 0, 0]), expected_b, places=5)
        self.assertAlmostEqual(float(prepared.tensor[0, 1, 0, 0]), expected_g, places=5)
        self.assertAlmostEqual(float(prepared.tensor[0, 2, 0, 0]), expected_r, places=5)

    def test_center_priors_match_official_half_stride_formula(self) -> None:
        priors = center_priors(320, 320, [8, 16, 32, 64])
        self.assertEqual(priors.shape, (2125, 4))
        np.testing.assert_array_equal(priors[0], np.array([4, 4, 8, 8]))
        np.testing.assert_array_equal(priors[1599], np.array([316, 316, 8, 8]))
        np.testing.assert_array_equal(priors[1600], np.array([8, 8, 16, 16]))
        np.testing.assert_array_equal(priors[-1], np.array([288, 288, 64, 64]))

    def test_synthetic_distribution_decodes_and_scales_to_original(self) -> None:
        prepared = prepare_image(Image.new("RGB", (640, 320), "white"), LOCK)
        raw = np.zeros((1, 2125, 112), dtype=np.float32)
        raw[0, 0, 0] = 0.95
        # Four distributions, each concentrated at distance bin 1. The first
        # official prior is (4,4) at stride 8, yielding [-4,-4,12,12] before
        # clipping and [0,0,24,12] after scaling back to 640x320.
        for side in range(4):
            start = 80 + side * 8
            raw[0, 0, start : start + 8] = -10
            raw[0, 0, start + 1] = 10
        detections = postprocess_predictions(
            raw,
            prepared,
            LABELS,
            LOCK,
            confidence_threshold=0.25,
            nms_iou_threshold=0.45,
            max_detections=100,
        )
        self.assertEqual(len(detections), 1)
        detection = detections[0]
        self.assertEqual(detection.class_id, 0)
        self.assertAlmostEqual(detection.confidence, 0.95, places=5)
        x1, y1, x2, y2 = detection.bbox_xyxy
        self.assertAlmostEqual(x1, 0.0, places=4)
        self.assertAlmostEqual(y1, 0.0, places=4)
        self.assertAlmostEqual(x2, 24.0, places=3)
        self.assertAlmostEqual(y2, 12.0, places=3)

    def test_wrong_output_shape_is_rejected(self) -> None:
        prepared = prepare_image(Image.new("RGB", (320, 320), "white"), LOCK)
        with self.assertRaisesRegex(ValueError, "Unexpected NanoDet output shape"):
            postprocess_predictions(
                np.zeros((1, 2125, 111), dtype=np.float32),
                prepared,
                LABELS,
                LOCK,
                confidence_threshold=0.25,
                nms_iou_threshold=0.45,
                max_detections=100,
            )


if __name__ == "__main__":
    unittest.main()
