from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.publish_detector_comparison import (
    DISCLAIMER,
    compare_entry,
    greedy_matches,
    require_pair,
    validate_artifact,
)


def detection(class_id: int, name: str, confidence: float, box: list[float]) -> dict:
    return {
        "class_id": class_id,
        "class_name": name,
        "confidence": confidence,
        "bbox_xyxy": box,
        "bbox_normalized_xyxy": [value / 100 for value in box],
        "area_pixels": max(0, box[2] - box[0]) * max(0, box[3] - box[1]),
        "area_fraction": 0.1,
    }


def entry(detector_id: str, detections: list[dict]) -> dict:
    classes: dict[str, int] = {}
    for item in detections:
        classes[item["class_name"]] = classes.get(item["class_name"], 0) + 1
    return {
        "schema_version": 1,
        "status": "success",
        "detector_id": detector_id,
        "image_sha256": "a" * 64,
        "sources": [{"prompt_id": "i0001", "category": "portrait"}],
        "detections": detections,
        "detection_count": len(detections),
        "class_counts": classes,
        "sidecar_file": f"object-detection/{detector_id}/detections/a.json",
    }


class DetectorComparisonTests(unittest.TestCase):
    def test_same_class_greedy_matching_is_deterministic(self) -> None:
        left = [
            detection(0, "person", 0.9, [0, 0, 50, 50]),
            detection(2, "car", 0.7, [60, 60, 100, 100]),
        ]
        right = [
            detection(0, "person", 0.8, [2, 2, 49, 49]),
            detection(2, "car", 0.6, [0, 60, 40, 100]),
        ]
        matches, unmatched_left, unmatched_right = greedy_matches(left, right)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["class_name"], "person")
        self.assertGreater(matches[0]["iou"], 0.8)
        self.assertEqual(unmatched_left, [1])
        self.assertEqual(unmatched_right, [1])

    def test_comparison_reports_agreement_not_accuracy(self) -> None:
        left = entry("yolox-tiny", [detection(0, "person", 0.9, [0, 0, 50, 50])])
        right = entry(
            "nanodet-plus-m-320",
            [
                detection(0, "person", 0.8, [1, 1, 50, 50]),
                detection(2, "car", 0.7, [60, 60, 90, 90]),
            ],
        )
        result = compare_entry(left, right)
        self.assertEqual(result["state"], "both-nonempty")
        self.assertEqual(result["shared_classes"], ["person"])
        self.assertEqual(result["nanodet_only_classes"], ["car"])
        self.assertEqual(result["matched_box_count"], 1)
        self.assertGreater(result["disagreement_score"], 0)
        self.assertNotIn("accuracy", result)
        self.assertIn("not ground-truth", DISCLAIMER)
        self.assertIn("not ground-truth labels or an accuracy benchmark", DISCLAIMER)

    def test_empty_states_are_explicit(self) -> None:
        both = compare_entry(entry("yolox-tiny", []), entry("nanodet-plus-m-320", []))
        self.assertEqual(both["state"], "both-empty")
        self.assertEqual(both["disagreement_score"], 0)
        only = compare_entry(
            entry("yolox-tiny", [detection(0, "person", 0.9, [0, 0, 10, 10])]),
            entry("nanodet-plus-m-320", []),
        )
        self.assertEqual(only["state"], "yolox-only-nonempty")
        self.assertGreater(only["disagreement_score"], 0.7)

    def test_pair_requires_exact_corpus_and_thresholds(self) -> None:
        base = {
            "analysis_batch_id": "detection-test",
            "corpus_fingerprint": "c" * 64,
            "quarantine_policy_digest": "q" * 64,
            "source_release_tags": ["media-exp-2026-07-13"],
            "canonical_image_sha256": ["a" * 64],
            "labels_sha256": "l" * 64,
            "thresholds": {"confidence": 0.25, "nms_iou": 0.45, "max_detections": 100},
            "detector_id": "yolox-tiny",
        }
        right = {**base, "detector_id": "nanodet-plus-m-320"}
        require_pair(base, right)
        mismatched = {**right, "corpus_fingerprint": "d" * 64}
        with self.assertRaisesRegex(ValueError, "corpus_fingerprint"):
            require_pair(base, mismatched)

    def test_artifact_validates_zip_hash_and_sidecar_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "release-assets"
            assets.mkdir()
            package = assets / "yolox-coco-metadata.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("object-detection/yolox-tiny/readme.txt", "ok")
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            entries_path = root / "package-root/object-detection/yolox-tiny/entries.json"
            entries_path.parent.mkdir(parents=True)
            entries_path.write_text(json.dumps([entry("yolox-tiny", [])]), encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "status": "success",
                "analysis_batch_id": "detection-test",
                "detector_id": "yolox-tiny",
                "corpus_fingerprint": "c" * 64,
                "quarantine_policy_digest": "q" * 64,
                "source_release_tags": ["media-exp-2026-07-13"],
                "canonical_image_sha256": ["a" * 64],
                "labels_sha256": "l" * 64,
                "model_sha256": "m" * 64,
                "thresholds": {"confidence": 0.25},
                "package_files": [
                    {
                        "name": package.name,
                        "size_bytes": package.stat().st_size,
                        "sha256": digest,
                    }
                ],
            }
            (root / "completion-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            loaded, entries = validate_artifact(root, "yolox-tiny")
            self.assertEqual(loaded["analysis_batch_id"], "detection-test")
            self.assertEqual(len(entries), 1)
            package.write_bytes(package.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                validate_artifact(root, "yolox-tiny")


if __name__ == "__main__":
    unittest.main()
