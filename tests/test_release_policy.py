from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from release_policy import (
    filter_manifest_runs,
    media_counts_from_file_records,
    quarantine_policy_digest,
    validate_publishable_run,
)


class ReleasePolicyTests(unittest.TestCase):
    def test_historical_fixture_and_empty_run_are_quarantined(self) -> None:
        runs = [
            {"run_id": "run_20260629_232751"},
            {"run_id": "run_20260629_233317"},
            {"run_id": "run_test"},
        ]
        included, excluded = filter_manifest_runs("media-exp-2026-06-29", runs)
        self.assertEqual([row["run_id"] for row in included], ["run_20260629_233317"])
        self.assertEqual(
            [row["run"]["run_id"] for row in excluded],
            ["run_20260629_232751", "run_test"],
        )

    def test_media_counts_use_manifest_file_records(self) -> None:
        counts = media_counts_from_file_records(
            [
                {"path": "media/images/i0001.png"},
                {"path": "media/images/i0002.webp"},
                {"path": "media/videos/v001.mp4"},
                {"path": "outputs.jsonl"},
            ]
        )
        self.assertEqual(counts, {"images": 2, "videos": 1})

    def test_publishable_run_requires_matching_events_and_media(self) -> None:
        valid = SimpleNamespace(
            run_id="run_20260720_120000",
            files=(
                {"path": "outputs.jsonl"},
                {"path": "media/images/i0001.png"},
                {"path": "media/videos/v001.mp4"},
            ),
            stats={"file_count": 3, "image_completed": 1, "video_completed": 1},
        )
        validate_publishable_run(valid)
        invalid = SimpleNamespace(
            run_id="run_20260720_120001",
            files=valid.files,
            stats={"file_count": 3, "image_completed": 2, "video_completed": 1},
        )
        with self.assertRaisesRegex(ValueError, "completion/media integrity mismatch"):
            validate_publishable_run(invalid)

    def test_test_named_and_empty_runs_cannot_be_published(self) -> None:
        with self.assertRaisesRegex(ValueError, "run ID must match"):
            validate_publishable_run(SimpleNamespace(run_id="run_test", files=(), stats={}))
        with self.assertRaisesRegex(ValueError, "empty runs"):
            validate_publishable_run(
                SimpleNamespace(
                    run_id="run_20260720_120000",
                    files=(),
                    stats={"file_count": 0},
                )
            )

    def test_quarantine_digest_is_stable_and_content_sensitive(self) -> None:
        first = quarantine_policy_digest()
        self.assertEqual(first, quarantine_policy_digest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.json"
            path.write_text(json.dumps({"schema_version": 1, "excluded_runs": []}), encoding="utf-8")
            self.assertNotEqual(first, quarantine_policy_digest(path))


if __name__ == "__main__":
    unittest.main()
