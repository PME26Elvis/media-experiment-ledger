from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReadmeInformationArchitectureTests(unittest.TestCase):
    def test_root_readmes_are_stable_landing_pages(self) -> None:
        for path, status_link, docs_link in (
            (ROOT / "README.md", "docs/PROJECT_STATUS.md", "docs/README.md"),
            (ROOT / "README.en.md", "docs/PROJECT_STATUS.en.md", "docs/README.en.md"),
        ):
            text = path.read_text(encoding="utf-8")
            self.assertIn(status_link, text)
            self.assertIn(docs_link, text)
            self.assertIn("media-detection-*", text)
            for marker in (
                "AUTO:LEDGER_STATS",
                "AUTO:ATLAS_HISTORY",
                "AUTO:YOLO_HISTORY",
                "NANODET:README",
            ):
                self.assertNotIn(marker, text)

    def test_generated_status_pages_own_all_history_markers(self) -> None:
        zh = (ROOT / "docs" / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        en = (ROOT / "docs" / "PROJECT_STATUS.en.md").read_text(encoding="utf-8")
        for marker in (
            "AUTO:LEDGER_STATS:START",
            "AUTO:ATLAS_HISTORY:START",
            "AUTO:YOLO_HISTORY:START",
            "NANODET:README:START",
        ):
            self.assertIn(marker, zh)
        for marker in (
            "AUTO:LEDGER_STATS_EN:START",
            "AUTO:ATLAS_HISTORY_EN:START",
            "AUTO:YOLO_HISTORY_EN:START",
            "NANODET:README:START",
        ):
            self.assertIn(marker, en)

    def test_atlas_and_legacy_yolo_writeback_target_status_pages(self) -> None:
        atlas = (ROOT / ".github" / "workflows" / "visual-analysis.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--readme docs/PROJECT_STATUS.md", atlas)
        self.assertIn("--readme-en docs/PROJECT_STATUS.en.md", atlas)
        self.assertNotIn("README.md", atlas)
        self.assertNotIn("README.en.md", atlas)

        yolo = (ROOT / ".github" / "workflows" / "yolo-object-detection.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--readme docs/PROJECT_STATUS.md", yolo)
        self.assertIn("--readme-en docs/PROJECT_STATUS.en.md", yolo)
        self.assertNotIn("paths=(data/yolo web/public/data/yolo README.md", yolo)

    def test_documentation_hubs_expose_operator_and_status_routes(self) -> None:
        zh = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        en = (ROOT / "docs" / "README.en.md").read_text(encoding="utf-8")
        for text, status in ((zh, "PROJECT_STATUS.md"), (en, "PROJECT_STATUS.en.md")):
            self.assertIn(status, text)
            self.assertIn("INPUT_ARCHIVE_WORKFLOW", text)
            self.assertIn("NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md", text)
            self.assertIn("PROJECT_CONTRACT.md", text)


if __name__ == "__main__":
    unittest.main()
