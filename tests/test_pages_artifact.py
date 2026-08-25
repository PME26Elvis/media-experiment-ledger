from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.prepare_pages_artifact import REPOSITORY_PREVIEW_MIRRORS, prepare


class PagesArtifactPreparationTests(unittest.TestCase):
    def test_prepare_removes_only_repo_backed_preview_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            data = site / "data"
            data.mkdir(parents=True)
            keep = data / "visual-analysis.json"
            keep.write_text('{"status":"published"}\n', encoding="utf-8")

            expected_files = 0
            expected_bytes = 0
            for index, relative in enumerate(REPOSITORY_PREVIEW_MIRRORS, 1):
                mirror = site / relative
                mirror.mkdir(parents=True)
                payload = bytes([index]) * (index * 17)
                (mirror / f"preview-{index}.bin").write_bytes(payload)
                expected_files += 1
                expected_bytes += len(payload)

            removed_files, removed_bytes = prepare(site)
            self.assertEqual(removed_files, expected_files)
            self.assertEqual(removed_bytes, expected_bytes)
            self.assertTrue(keep.is_file())
            self.assertEqual(keep.read_text(encoding="utf-8"), '{"status":"published"}\n')
            for relative in REPOSITORY_PREVIEW_MIRRORS:
                self.assertFalse((site / relative).exists())

    def test_prepare_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            site.mkdir()
            self.assertEqual(prepare(site), (0, 0))
            self.assertEqual(prepare(site), (0, 0))

    def test_prepare_rejects_missing_site(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Missing built site directory"):
                prepare(Path(temp) / "missing")


if __name__ == "__main__":
    unittest.main()
