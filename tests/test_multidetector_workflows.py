from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MultiDetectorWorkflowTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_inference_workflows_are_artifact_only_and_read_only(self) -> None:
        for name, artifact in (
            ("detector-yolox-inference.yml", "detector-yolox-"),
            ("detector-nanodet-inference.yml", "detector-nanodet-"),
        ):
            workflow = self.text(name)
            self.assertIn("contents: read", workflow)
            self.assertNotIn("contents: write", workflow)
            self.assertIn("actions/upload-artifact@v4", workflow)
            self.assertIn(artifact, workflow)
            self.assertNotIn("gh release create", workflow)
            self.assertNotIn("git push origin", workflow)
            self.assertIn("complete canonical corpus from scratch", workflow)

    def test_publisher_downloads_exact_run_ids_and_trusted_main_code(self) -> None:
        workflow = self.text("detector-comparison-publish.yml")
        self.assertIn("run-id: ${{ needs.resolve.outputs.yolox_run_id }}", workflow)
        self.assertIn("run-id: ${{ needs.resolve.outputs.nanodet_run_id }}", workflow)
        self.assertIn("github-token: ${{ github.token }}", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("Detector artifacts do not match", (ROOT / "tools" / "publish_detector_comparison.py").read_text(encoding="utf-8"))
        self.assertNotIn("latest successful YOLO", workflow)
        self.assertNotIn("latest successful NanoDet", workflow)

    def test_publisher_is_independent_from_atlas(self) -> None:
        workflow = self.text("detector-comparison-publish.yml")
        self.assertNotIn("media-analysis-", workflow)
        self.assertNotIn("visual-analysis", workflow)
        self.assertNotIn("data/visual-analysis", workflow)
        spec = (ROOT / "docs" / "NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("Atlas impact: **none**", spec)
        self.assertIn("not ground-truth labels or an accuracy benchmark", spec)

    def test_legacy_yolo_release_workflow_must_be_manual_after_switch(self) -> None:
        workflow = self.text("yolo-object-detection.yml")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("  push:\n", workflow)
        self.assertIn("legacy", workflow.lower())


if __name__ == "__main__":
    unittest.main()
