from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NanoDetPipelineSpecTests(unittest.TestCase):
    def test_spec_requires_exact_run_pairing_and_no_accuracy_claim(self) -> None:
        spec = (
            ROOT / "docs" / "NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md"
        ).read_text(encoding="utf-8")
        for token in (
            "Status: **`implemented_pending_production`**",
            "detector-yolox-inference.yml",
            "detector-nanodet-inference.yml",
            "detector-comparison-publish.yml",
            "media-detection-all-",
            "exact run IDs",
            "analysis_batch_id",
            "Original | YOLOX-Tiny | NanoDet-Plus",
            "not ground-truth labels or an accuracy benchmark",
            "Atlas impact: **none**",
            '"Latest successful YOLO" plus "latest successful NanoDet" is forbidden',
            "official immutable pre-exported ONNX",
            "4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610",
        ):
            self.assertIn(token, spec)
        self.assertIn("workflow artifacts are transport", spec.lower())

    def test_machine_contract_marks_implementation_pending_production(self) -> None:
        contract = json.loads(
            (ROOT / "project-contract.json").read_text(encoding="utf-8")
        )["planned_analysis"]["multi_detector_yolox_nanodet"]
        self.assertEqual(contract["status"], "implemented_pending_production")
        self.assertEqual(contract["atlas_coupling"], "none")
        self.assertIn("exact workflow run IDs", contract["artifact_pairing"])
        self.assertEqual(contract["nanodet_model_lock"], "object-detection/nanodet-model-lock.json")
        self.assertEqual(contract["detector_lab_route"], "detector-lab")
        self.assertFalse(contract["persistent_state"])
        self.assertFalse(contract["cross_run_cache_skip"])
        self.assertFalse(contract["published_result_reuse"])
        for key in (
            "production_release",
            "production_yolox_run_id",
            "production_nanodet_run_id",
            "production_publisher_run_id",
            "production_writeback_commit",
        ):
            self.assertIsNone(contract[key])


if __name__ == "__main__":
    unittest.main()
