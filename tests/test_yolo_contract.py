from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class YoloContractTests(unittest.TestCase):
    def test_atlas_preview_configuration_remains_stable(self) -> None:
        config = json.loads((ROOT / "visual-analysis" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["release_notes_image_highlights"], 15)
        self.assertEqual(config["release_notes_image_min_samples"], 4)
        self.assertEqual(config["release_notes_video_highlights"], "all")
        self.assertEqual(config["release_notes_video_min_samples"], 2)
        self.assertEqual(config["prompts_per_bundle"], 15)
        self.assertEqual(config["video_prompts_per_bundle"], 15)
        publisher = (ROOT / "tools" / "prompt_atlas_publish.py").read_text(encoding="utf-8")
        self.assertIn('title="Image highlights"', publisher)
        self.assertIn('title="Video highlights"', publisher)
        self.assertIn("repeatability comparison]", publisher)

    def test_yolo_pipeline_has_verified_independent_release_contract(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "yolo-object-detection.yml").read_text(encoding="utf-8")
        self.assertIn("timeout-minutes: 350", workflow)
        self.assertIn("tools/build_yolo_detection.py", workflow)
        self.assertNotIn("visual-analysis.yml", workflow)
        self.assertNotIn("media-analysis-", workflow)
        contract = json.loads((ROOT / "project-contract.json").read_text(encoding="utf-8"))["planned_analysis"]["yolo_object_detection"]
        self.assertEqual(contract["status"], "implemented")
        self.assertEqual(contract["production_release"], "media-yolo-all-2026-07-13-v1")
        self.assertEqual(contract["production_canonical_images"], 387)
        self.assertEqual(contract["production_images_with_detections"], 313)
        self.assertEqual(contract["production_total_detections"], 1533)
        self.assertEqual(contract["atlas_coupling"], "none")
        self.assertFalse(contract["matrix_sharding_v1"])
        self.assertFalse(contract["persistent_state"])
        self.assertFalse(contract["cross_run_cache_skip"])
        self.assertFalse(contract["published_result_reuse"])


if __name__ == "__main__":
    unittest.main()
