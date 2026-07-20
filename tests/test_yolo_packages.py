from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.yolo_packages import choose_previews, deterministic_zip, summarize
from tools.yolo_publish import choose_tag


class YoloPackageTests(unittest.TestCase):
    def test_tag_always_advances_published_versions(self) -> None:
        rows = [
            {"tagName": "media-yolo-all-2026-07-13-v1", "isDraft": False},
            {"tagName": "media-analysis-all-deadbeef-v99", "isDraft": False},
        ]
        self.assertEqual(
            choose_tag("2026-07-13", rows),
            ("media-yolo-all-2026-07-13-v2", False),
        )

    def test_draft_shell_can_be_reused_but_not_results(self) -> None:
        rows = [
            {"tagName": "media-yolo-all-2026-07-13-v3", "isDraft": True}
        ]
        self.assertEqual(
            choose_tag("2026-07-13", rows),
            ("media-yolo-all-2026-07-13-v3", True),
        )

    def test_summary_and_preview_selection(self) -> None:
        entries = [
            {
                "status": "success",
                "image_sha256": "a",
                "detection_count": 2,
                "class_counts": {"person": 2},
                "top_classes": ["person"],
                "max_confidence": 0.9,
                "annotated_file": "a.jpg",
                "sources": [{"prompt_id": "i1", "release_tag": "r"}],
                "detections": [{"confidence": 0.9}],
            },
            {
                "status": "success",
                "image_sha256": "b",
                "detection_count": 0,
                "class_counts": {},
                "top_classes": [],
                "max_confidence": 0,
                "annotated_file": "b.jpg",
                "sources": [{"prompt_id": "i2", "release_tag": "r"}],
                "detections": [],
            },
        ]
        summary = summarize(entries)
        self.assertEqual(summary["total_detections"], 2)
        self.assertEqual(summary["empty_detection_images"], 1)
        self.assertEqual(len(choose_previews(entries, limit=2)), 2)

    def test_deterministic_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            first = root / "first.zip"
            second = root / "second.zip"
            deterministic_zip(first, root, [root / "a.txt"])
            deterministic_zip(second, root, [root / "a.txt"])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.read("a.txt"), b"hello")


if __name__ == "__main__":
    unittest.main()
