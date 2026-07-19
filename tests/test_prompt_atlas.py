from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.prompt_atlas_core import (
    Sample,
    cohort_identity,
    deduplicate_samples,
    grid_shape,
    member_matches,
    normalized_settings,
    render_card,
    select_primary,
    temporal_quantiles,
)
from tools.prompt_atlas_github import next_analysis_tag


def sample(index: int, *, source_tag: str = "media-exp-2026-07-01", digest: str | None = None) -> Sample:
    return Sample(
        prompt_id="i0001",
        category="product",
        prompt="A ceramic mug on a desk in warm morning light.",
        model="model-a",
        settings={"model": "model-a", "size": "1024x1024"},
        cohort_id="cohort",
        source_tag=source_tag,
        release_published_at=f"2026-07-{index:02d}T00:00:00Z",
        run_id=f"run_{index:02d}",
        timestamp=f"2026-07-{index:02d}T00:00:00Z",
        finished_at=f"2026-07-{index:02d}T00:01:00Z",
        local_path=f"media/images/i0001-{index}.png",
        seed=index,
        extracted_path=f"/tmp/i0001-{index}.png",
        sha256=digest or f"digest-{index}",
        width=128,
        height=128,
    )


class PromptAtlasTests(unittest.TestCase):
    def test_settings_ignore_prompt_and_response_format(self) -> None:
        first = normalized_settings({"model": "m", "prompt": "one", "size": "1x1", "extra_body": {"response_format": "url"}})
        second = normalized_settings({"model": "m", "prompt": "two", "size": "1x1", "extra_body": {"response_format": "b64_json"}})
        self.assertEqual(first, second)
        self.assertEqual(cohort_identity("i1", "m", first), cohort_identity("i1", "m", second))

    def test_member_matching_is_precise(self) -> None:
        self.assertTrue(member_matches("media/images/i0001.png", "i0001"))
        self.assertFalse(member_matches("media/videos/i0001.png", "i0001"))
        self.assertFalse(member_matches("media/images/i00010.png", "i0001"))
        self.assertFalse(member_matches("media/images/i0001.json", "i0001"))

    def test_dynamic_grid_shapes(self) -> None:
        self.assertEqual(grid_shape(2), (2, 1, 2))
        self.assertEqual(grid_shape(3), (2, 2, 3))
        self.assertEqual(grid_shape(9, extended=True), (4, 2, 8))

    def test_primary_selection_preserves_current(self) -> None:
        rows = [sample(index) for index in range(1, 8)]
        rows[-1].source_tag = "media-exp-2026-07-07"
        selected = select_primary(rows, "media-exp-2026-07-07")
        self.assertEqual(len(selected), 4)
        self.assertIs(selected[-1], rows[-1])
        self.assertIs(selected[0], rows[0])

    def test_temporal_quantiles_are_deterministic(self) -> None:
        rows = [sample(index) for index in range(1, 11)]
        first = [item.run_id for item in temporal_quantiles(rows, 8)]
        second = [item.run_id for item in temporal_quantiles(rows, 8)]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "run_01")
        self.assertEqual(first[-1], "run_10")

    def test_exact_duplicate_media_is_removed(self) -> None:
        rows = [sample(1, digest="same"), sample(2, digest="same"), sample(3, digest="other")]
        self.assertEqual([item.run_id for item in deduplicate_samples(rows)], ["run_01", "run_03"])
        rows[1].source_tag = "media-exp-2026-07-02"
        self.assertEqual([item.run_id for item in deduplicate_samples(rows, preferred_tag="media-exp-2026-07-02")], ["run_02", "run_03"])

    def test_analysis_tag_versions_without_state(self) -> None:
        existing = ["media-analysis-2026-07-12-v1", "media-analysis-2026-07-12-v3"]
        self.assertEqual(next_analysis_tag("media-exp-2026-07-12", existing), "media-analysis-2026-07-12-v4")
        self.assertEqual(next_analysis_tag("media-exp-2026-07-12-s01", existing), "media-analysis-2026-07-12-s01-v1")

    def test_render_two_and_three_sample_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [sample(index, source_tag="media-exp-2026-07-03" if index == 3 else "media-exp-2026-07-01") for index in range(1, 4)]
            for index, item in enumerate(rows, 1):
                image_path = root / f"{index}.png"
                Image.new("RGB", (128 + index, 96 + index), (index * 30, 50, 90)).save(image_path)
                item.extracted_path = str(image_path)
            config = {"cell_size": 240, "header_height": 150, "label_height": 58, "margin": 16, "gap": 8, "prompt_max_lines": 2}
            two_path = root / "two.jpg"
            render_card(two_path, prompt_id="i0001", category="product", prompt=rows[0].prompt, model="model-a", cohort_id="cohort", samples=rows[:2], roles=["Historical", "Current"], config=config)
            three_path = root / "three.jpg"
            render_card(three_path, prompt_id="i0001", category="product", prompt=rows[0].prompt, model="model-a", cohort_id="cohort", samples=rows, roles=["Earliest", "Historical", "Current"], config=config)
            for path in (two_path, three_path):
                self.assertTrue(path.exists())
                with Image.open(path) as rendered:
                    self.assertGreater(rendered.width, 400)
                    self.assertGreater(rendered.height, 300)


if __name__ == "__main__":
    unittest.main()
