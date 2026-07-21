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
            "Status: **`specified_not_implemented`**",
            "detector-yolox-inference.yml",
            "detector-nanodet-inference.yml",
            "detector-comparison-publish.yml",
            "media-detection-all-",
            "exact run IDs",
            "analysis_batch_id",
            "Original | YOLOX-Tiny | NanoDet-Plus",
            "not ground-truth labels or an accuracy benchmark",
            "Atlas impact: **none**",
        ):
            self.assertIn(token, spec)
        self.assertIn("Never pair", spec)
        self.assertIn("workflow artifacts are transport", spec.lower())

    def test_machine_contract_marks_pipeline_as_planned_only(self) -> None:
        contract = json.loads(
            (ROOT / "project-contract.json").read_text(encoding="utf-8")
        )["planned_analysis"]["multi_detector_yolox_nanodet"]
        self.assertEqual(contract["status"], "specified_not_implemented")
        self.assertEqual(contract["atlas_coupling"], "none")
        self.assertEqual(contract["publisher_initial_mode"], "manual exact run-ID inputs")
        self.assertFalse(contract["persistent_state"])
        self.assertFalse(contract["cross_run_cache_skip"])
        self.assertFalse(contract["published_result_reuse"])


if __name__ == "__main__":
    unittest.main()
