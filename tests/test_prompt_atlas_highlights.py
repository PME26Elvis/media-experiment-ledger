from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from prompt_atlas_publish import (
    choose_highlights,
    choose_release_highlight_groups,
    configured_highlight_limit,
    publication_result,
)


def entry(
    prompt_id: str,
    *,
    media_type: str = "image",
    category: str = "product",
    samples: int = 4,
) -> SimpleNamespace:
    return SimpleNamespace(
        media_type=media_type,
        prompt_id=prompt_id,
        category=category,
        prompt=f"Prompt for {prompt_id}",
        model="model-a",
        cohort_id=f"cohort-{prompt_id}",
        sample_count=samples,
        bundle_file=f"bundle-{media_type}.zip",
    )


class PromptAtlasHighlightTests(unittest.TestCase):
    def test_configured_limit_accepts_all(self) -> None:
        self.assertIsNone(configured_highlight_limit("all", 2))
        self.assertIsNone(configured_highlight_limit(" ALL ", 2))
        self.assertEqual(configured_highlight_limit(15, 2), 15)
        self.assertEqual(configured_highlight_limit(-3, 2), 0)

    def test_finite_selection_covers_categories_with_strongest_cohort(self) -> None:
        rows = [
            entry("i0001", category="product", samples=10),
            entry("i0002", category="product", samples=9),
            entry("i0003", category="nature", samples=8),
            entry("i0004", category="nature", samples=7),
            entry("i0005", category="ui", samples=6),
            entry("i0006", category="ui", samples=5),
        ]
        selected = choose_highlights(
            rows,
            3,
            media="image",
            min_samples=4,
            category_diversity=True,
        )
        self.assertEqual(
            [item.prompt_id for item in selected],
            ["i0001", "i0003", "i0005"],
        )

    def test_image_policy_is_capped_and_excludes_thin_tail(self) -> None:
        rows = [
            entry(
                f"i{index:04d}",
                category=f"category-{index % 5}",
                samples=10 - (index % 6),
            )
            for index in range(1, 19)
        ]
        rows.extend(
            [
                entry("i0098", category="rare-low", samples=3),
                entry("i0099", category="rare-low", samples=2),
            ]
        )
        groups = choose_release_highlight_groups(
            rows,
            {
                "release_notes_image_highlights": 15,
                "release_notes_image_min_samples": 4,
                "release_notes_video_highlights": "all",
            },
        )
        self.assertEqual(len(groups["image"]), 15)
        self.assertTrue(all(item.sample_count >= 4 for item in groups["image"]))
        self.assertNotIn("i0098", {item.prompt_id for item in groups["image"]})
        self.assertNotIn("i0099", {item.prompt_id for item in groups["image"]})

    def test_video_all_policy_includes_every_comparable_prompt_stably(self) -> None:
        rows = [
            entry("v007", media_type="video", category="g", samples=4),
            entry("v001", media_type="video", category="a", samples=6),
            entry("v004", media_type="video", category="d", samples=5),
            entry("v002", media_type="video", category="b", samples=5),
            entry("v006", media_type="video", category="f", samples=4),
            entry("v003", media_type="video", category="c", samples=5),
            entry("v005", media_type="video", category="e", samples=4),
        ]
        groups = choose_release_highlight_groups(
            rows,
            {
                "release_notes_image_highlights": 15,
                "release_notes_video_highlights": "all",
                "release_notes_video_min_samples": 2,
            },
        )
        self.assertEqual(
            [item.prompt_id for item in groups["video"]],
            ["v001", "v002", "v003", "v004", "v005", "v006", "v007"],
        )

    def test_publication_result_keeps_combined_and_typed_highlights(self) -> None:
        rows = [
            entry("i0001", samples=8),
            entry("v001", media_type="video", category="video", samples=6),
            entry("v002", media_type="video", category="video", samples=5),
        ]
        result = publication_result(
            "media-analysis-all-test-v1",
            "https://example.invalid/release",
            {
                "prompt-repeatability-atlas-complete-part001.zip": "complete",
                "atlas-metadata.zip": "metadata",
            },
            rows,
            {
                "release_notes_image_highlights": 15,
                "release_notes_image_min_samples": 4,
                "release_notes_video_highlights": "all",
            },
            resumed=False,
            reused=False,
        )
        self.assertEqual(len(result["image_highlights"]), 1)
        self.assertEqual(len(result["video_highlights"]), 2)
        self.assertEqual(
            result["highlights"],
            [*result["image_highlights"], *result["video_highlights"]],
        )
        self.assertEqual(result["archive_url"], "complete")


if __name__ == "__main__":
    unittest.main()
