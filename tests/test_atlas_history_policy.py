from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from atlas_history_policy import historical_metric, load_atlas_history_overrides


class AtlasHistoryPolicyTests(unittest.TestCase):
    def test_explicit_report_value_wins_over_normal_legacy_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "overrides.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "overrides": {
                            "legacy": {
                                "images": 999,
                                "videos": 999,
                                "reason": "test override",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = {
                "metadata_image_samples": 3,
                "metadata_video_samples": 1,
            }
            self.assertEqual(
                historical_metric("legacy", report, "images", overrides_path=path),
                3,
            )
            self.assertEqual(
                historical_metric("legacy", report, "videos", overrides_path=path),
                1,
            )

    def test_authoritative_override_can_correct_proven_corrupt_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "overrides.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "overrides": {
                            "legacy": {
                                "images": 3,
                                "videos": 1,
                                "authoritative": True,
                                "reason": "audited corrupt global count",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            polluted = {
                "metadata_image_samples": 937,
                "metadata_video_samples": 40,
            }
            self.assertEqual(
                historical_metric("legacy", polluted, "images", overrides_path=path),
                3,
            )
            self.assertEqual(
                historical_metric("legacy", polluted, "videos", overrides_path=path),
                1,
            )

    def test_known_legacy_releases_use_audited_overrides(self) -> None:
        overrides = load_atlas_history_overrides()
        self.assertEqual(
            overrides["media-analysis-all-f5fdcae2c78b-v1"]["videos"],
            40,
        )
        single = overrides["media-analysis-2026-07-13-v1"]
        self.assertTrue(single["authoritative"])
        polluted = {
            "metadata_image_samples": 937,
            "metadata_video_samples": 1,
        }
        self.assertEqual(
            historical_metric(
                "media-analysis-2026-07-13-v1",
                polluted,
                "images",
            ),
            3,
        )
        self.assertEqual(
            historical_metric(
                "media-analysis-2026-07-13-v1",
                polluted,
                "videos",
            ),
            1,
        )

    def test_unknown_legacy_release_stays_unknown(self) -> None:
        self.assertIsNone(historical_metric("unknown-legacy", {}, "images"))
        self.assertIsNone(historical_metric("unknown-legacy", {}, "videos"))

    def test_current_totals_cannot_enter_the_resolution_api(self) -> None:
        with self.assertRaises(TypeError):
            historical_metric("unknown", {}, "images", current_total=387)  # type: ignore[call-arg]

    def test_invalid_override_requires_reason_nonnegative_counts_and_boolean_flag(self) -> None:
        invalid_values = [
            {"images": -1},
            {"images": 1, "reason": "x", "authoritative": "yes"},
            {"reason": "x", "authoritative": True},
        ]
        for item in invalid_values:
            with self.subTest(item=item), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "overrides.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "overrides": {"bad": item},
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    load_atlas_history_overrides(path)


if __name__ == "__main__":
    unittest.main()
