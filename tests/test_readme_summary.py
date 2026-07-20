from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import update_readme_summary as summary


class ReadmeSummaryTests(unittest.TestCase):
    def test_snapshot_releases_are_excluded_and_duplicate_runs_are_not_double_counted(self) -> None:
        rows = [
            {"tagName": "media-input-2026-07-01-abc", "publishedAt": "2026-07-01T00:00:00Z"},
            {"tagName": "media-exp-2026-07-01", "publishedAt": "2026-07-01T01:00:00Z"},
            {"tagName": "media-exp-2026-07-02", "publishedAt": "2026-07-02T01:00:00Z"},
            {"tagName": "media-analysis-all-abc-v1", "publishedAt": "2026-07-02T02:00:00Z"},
        ]
        manifests = {
            "media-exp-2026-07-01": [
                {
                    "runs": [
                        {
                            "run_id": "run-a",
                            "digest": "digest-a",
                            "stats": {"image_completed": 10, "video_completed": 2},
                        }
                    ]
                }
            ],
            "media-exp-2026-07-02": [
                {
                    "runs": [
                        {
                            "run_id": "run-a",
                            "digest": "digest-a",
                            "stats": {"image_completed": 10, "video_completed": 2},
                        },
                        {
                            "run_id": "run-b",
                            "digest": "digest-b",
                            "stats": {"image_completed": 3, "video_completed": 1},
                        },
                    ]
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp, patch.object(
            summary,
            "release_manifests",
            side_effect=lambda repo, tag, root: manifests.get(tag, []),
        ), patch.object(summary, "fallback_output_counts", return_value=(0, 0)):
            totals = summary.summarize_experiments(rows, "owner/repo", Path(temp))

        self.assertEqual(totals.release_count, 2)
        self.assertEqual(totals.date_from, "2026-07-01")
        self.assertEqual(totals.date_to, "2026-07-02")
        self.assertEqual(totals.images, 13)
        self.assertEqual(totals.videos, 3)
        self.assertNotIn("media-input-2026-07-01-abc", totals.per_release)

    def test_report_tags_preserve_historical_atlas_totals(self) -> None:
        totals = summary.ExperimentTotals(
            release_count=3,
            date_from="2026-07-01",
            date_to="2026-07-03",
            images=60,
            videos=6,
            per_release={
                "media-exp-2026-07-01": {"date": "2026-07-01", "images": 10, "videos": 1},
                "media-exp-2026-07-02": {"date": "2026-07-02", "images": 20, "videos": 2},
                "media-exp-2026-07-03": {"date": "2026-07-03", "images": 30, "videos": 3},
            },
        )
        report = {
            "release_tags": ["media-exp-2026-07-01", "media-exp-2026-07-02"],
            "date_from": "2026-07-01",
            "date_to": "2026-07-02",
        }
        self.assertEqual(
            summary.tags_for_report(report, totals),
            ["media-exp-2026-07-01", "media-exp-2026-07-02"],
        )

    def test_legacy_source_tag_is_supported(self) -> None:
        totals = summary.ExperimentTotals(
            release_count=1,
            date_from="2026-07-01",
            date_to="2026-07-01",
            images=4,
            videos=1,
            per_release={
                "media-exp-2026-07-01": {"date": "2026-07-01", "images": 4, "videos": 1}
            },
        )
        self.assertEqual(
            summary.tags_for_report({"source_tag": "media-exp-2026-07-01"}, totals),
            ["media-exp-2026-07-01"],
        )

    def test_replace_block_changes_only_marked_region(self) -> None:
        original = "before\n<!-- START -->\nold\n<!-- END -->\nafter\n"
        updated = summary.replace_block(original, "<!-- START -->", "<!-- END -->", "new")
        self.assertEqual(updated, "before\n<!-- START -->\nnew\n<!-- END -->\nafter\n")
        with self.assertRaises(ValueError):
            summary.replace_block("missing", "<!-- START -->", "<!-- END -->", "new")

    def test_update_readmes_writes_bilingual_tables(self) -> None:
        totals = summary.ExperimentTotals(
            release_count=2,
            date_from="2026-07-01",
            date_to="2026-07-02",
            images=13,
            videos=3,
            per_release={},
        )
        history = [
            summary.AtlasHistoryRow(
                published_at="2026-07-02T12:00:00Z",
                tag="media-analysis-all-abc-v1",
                name="全域重現性圖譜",
                scope="2026-07-01 → 2026-07-02",
                images=13,
                videos=3,
                comparable_prompts=5,
                url="https://github.com/o/r/releases/tag/media-analysis-all-abc-v1",
            )
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            zh = root / "README.md"
            en = root / "README.en.md"
            zh.write_text(
                "\n".join(
                    [
                        summary.ZH_STATS_START,
                        "old",
                        summary.ZH_STATS_END,
                        summary.ZH_ATLAS_START,
                        "old",
                        summary.ZH_ATLAS_END,
                    ]
                ),
                encoding="utf-8",
            )
            en.write_text(
                "\n".join(
                    [
                        summary.EN_STATS_START,
                        "old",
                        summary.EN_STATS_END,
                        summary.EN_ATLAS_START,
                        "old",
                        summary.EN_ATLAS_END,
                    ]
                ),
                encoding="utf-8",
            )
            summary.update_readmes(zh, en, totals, history)
            zh_text = zh.read_text(encoding="utf-8")
            en_text = en.read_text(encoding="utf-8")

        self.assertIn("| 圖片總數 | 13 |", zh_text)
        self.assertIn("| 影片總數 | 3 |", zh_text)
        self.assertIn("media-analysis-all-abc-v1", zh_text)
        self.assertIn("| Total images | 13 |", en_text)
        self.assertIn("| Total videos | 3 |", en_text)


if __name__ == "__main__":
    unittest.main()
