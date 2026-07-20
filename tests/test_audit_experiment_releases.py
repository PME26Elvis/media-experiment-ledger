from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_experiment_releases import audit_release_directory, render_release_notes


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class ExperimentReleaseAuditTests(unittest.TestCase):
    def test_audit_separates_canonical_and_quarantined_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_id = "run_20260629_233317"
            fixture_id = "run_test"
            image_member = "media/images/i0001.png"
            archive_name = f"{canonical_id}-images.zip"
            with zipfile.ZipFile(root / archive_name, "w") as archive:
                archive.writestr(image_member, b"fake-image-bytes")
            write_jsonl(
                root / f"{canonical_id}-outputs.jsonl",
                [{"event": "image_completed", "prompt_id": "i0001"}],
            )
            write_jsonl(
                root / f"{fixture_id}-outputs.jsonl",
                [{"event": "image_completed", "prompt_id": f"i{index:04d}"} for index in range(550)],
            )
            manifest = {
                "experiment_date_taipei": "2026-06-29",
                "content_digest": "digest",
                "runs": [
                    {
                        "run_id": canonical_id,
                        "digest": "a",
                        "stats": {"image_completed": 1, "video_completed": 0, "file_count": 2},
                        "files": [
                            {"path": "outputs.jsonl"},
                            {"path": image_member},
                        ],
                        "assets": [
                            {
                                "name": archive_name,
                                "kind": "images",
                                "size_bytes": (root / archive_name).stat().st_size,
                                "sha256": "",
                            }
                        ],
                    },
                    {
                        "run_id": fixture_id,
                        "digest": "b",
                        "stats": {"image_completed": 550, "video_completed": 7, "file_count": 1, "source_bytes": 352949},
                        "files": [{"path": "outputs.jsonl"}],
                        "assets": [],
                    },
                ],
            }
            (root / "manifest-2026-06-29.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit_release_directory(
                "media-exp-2026-06-29",
                root,
                verify_archives=True,
            )
            self.assertEqual(result["canonical_runs"], 1)
            self.assertEqual(result["quarantined_runs"], 1)
            self.assertEqual(result["totals"]["archived_images"], 1)
            self.assertEqual(result["totals"]["api_image_completed"], 1)
            self.assertEqual(result["status"], "corrected")
            notes = render_release_notes(result)
            self.assertIn("API image completion events: **1**", notes)
            self.assertIn("Archived image files: **1**", notes)
            self.assertIn("`run_test`", notes)
            self.assertNotIn("API image completion events: **550**", notes)


if __name__ == "__main__":
    unittest.main()
