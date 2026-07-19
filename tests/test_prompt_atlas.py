from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_prompt_atlas import create_release_packages
from prompt_atlas_core import (
    AtlasEntry,
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
from prompt_atlas_github import (
    analysis_tag_for_dataset,
    dataset_fingerprint,
    group_candidates,
    release_asset_url,
)


def sample(
    index: int,
    *,
    source_tag: str = "media-exp-2026-07-01",
    digest: str | None = None,
    prompt_id: str = "i0001",
) -> Sample:
    return Sample(
        prompt_id=prompt_id,
        category="product",
        prompt="A ceramic mug on a desk in warm morning light.",
        model="model-a",
        settings={"model": "model-a", "size": "1024x1024"},
        cohort_id=cohort_identity(
            prompt_id,
            "model-a",
            {"model": "model-a", "size": "1024x1024"},
        ),
        source_tag=source_tag,
        release_published_at=f"2026-07-{index:02d}T00:00:00Z",
        run_id=f"run_{index:02d}",
        timestamp=f"2026-07-{index:02d}T00:00:00Z",
        finished_at=f"2026-07-{index:02d}T00:01:00Z",
        local_path=f"media/images/{prompt_id}.png",
        seed=index,
        extracted_path=f"/tmp/{prompt_id}-{index}.png",
        sha256=digest or f"digest-{index}",
        width=128,
        height=128,
    )


class PromptAtlasTests(unittest.TestCase):
    def test_settings_ignore_prompt_and_response_format(self) -> None:
        first = normalized_settings(
            {
                "model": "m",
                "prompt": "one",
                "size": "1x1",
                "extra_body": {"response_format": "url"},
            }
        )
        second = normalized_settings(
            {
                "model": "m",
                "prompt": "two",
                "size": "1x1",
                "extra_body": {"response_format": "b64_json"},
            }
        )
        self.assertEqual(first, second)
        self.assertEqual(
            cohort_identity("i1", "m", first),
            cohort_identity("i1", "m", second),
        )

    def test_member_matching_is_precise(self) -> None:
        self.assertTrue(member_matches("media/images/i0001.png", "i0001"))
        self.assertFalse(member_matches("media/videos/i0001.png", "i0001"))
        self.assertFalse(member_matches("media/images/i00010.png", "i0001"))
        self.assertFalse(member_matches("media/images/i0001.json", "i0001"))

    def test_dynamic_grid_shapes_expand_to_sixteen(self) -> None:
        self.assertEqual(grid_shape(2), (2, 1, 2))
        self.assertEqual(grid_shape(3), (2, 2, 3))
        self.assertEqual(grid_shape(9, extended=True), (4, 3, 9))
        self.assertEqual(grid_shape(20, extended=True), (4, 4, 16))

    def test_primary_selection_uses_latest_cohort_sample(self) -> None:
        rows = [sample(index) for index in range(1, 8)]
        selected = select_primary(rows)
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
        rows = [
            sample(1, digest="same"),
            sample(2, digest="same"),
            sample(3, digest="other"),
        ]
        self.assertEqual(
            [item.run_id for item in deduplicate_samples(rows)],
            ["run_01", "run_03"],
        )
        rows[1].source_tag = "media-exp-2026-07-02"
        self.assertEqual(
            [
                item.run_id
                for item in deduplicate_samples(
                    rows,
                    preferred_tag="media-exp-2026-07-02",
                )
            ],
            ["run_02", "run_03"],
        )

    def test_global_groups_include_cohorts_absent_from_latest_release(self) -> None:
        older = [sample(1), sample(2)]
        newer = [
            sample(3, source_tag="media-exp-2026-07-03", prompt_id="i0002"),
            sample(4, source_tag="media-exp-2026-07-04", prompt_id="i0002"),
        ]
        groups = group_candidates([*older, *newer], "all")
        self.assertEqual(len(groups), 2)
        legacy = group_candidates([*older, *newer], "media-exp-2026-07-04")
        self.assertEqual(len(legacy), 1)

    def test_dataset_fingerprint_uses_all_release_tags_and_policy(self) -> None:
        rows = [
            {"tagName": "media-exp-2026-07-01", "publishedAt": "2026-07-01T00:00:00Z"},
            {"tagName": "media-exp-2026-07-02", "publishedAt": "2026-07-02T00:00:00Z"},
        ]
        first = dataset_fingerprint(rows, {"extended_max_samples": 16})
        self.assertEqual(first, dataset_fingerprint(rows, {"extended_max_samples": 16}))
        self.assertNotEqual(first, dataset_fingerprint(rows[:1], {"extended_max_samples": 16}))
        self.assertNotEqual(first, dataset_fingerprint(rows, {"extended_max_samples": 8}))

    def test_analysis_tag_reuses_published_fingerprint_without_force(self) -> None:
        fingerprint = "a" * 64
        releases = [{"tagName": "media-analysis-all-aaaaaaaaaaaa-v1", "isDraft": False}]
        self.assertEqual(
            analysis_tag_for_dataset(fingerprint, releases),
            ("media-analysis-all-aaaaaaaaaaaa-v1", False, True),
        )
        self.assertEqual(
            analysis_tag_for_dataset(fingerprint, releases, force=True),
            ("media-analysis-all-aaaaaaaaaaaa-v2", False, False),
        )

    def test_draft_resume_precedes_new_version(self) -> None:
        fingerprint = "b" * 64
        releases = [
            {"tagName": "media-analysis-all-bbbbbbbbbbbb-v1", "isDraft": False},
            {"tagName": "media-analysis-all-bbbbbbbbbbbb-v2", "isDraft": True},
        ]
        self.assertEqual(
            analysis_tag_for_dataset(fingerprint, releases),
            ("media-analysis-all-bbbbbbbbbbbb-v2", True, False),
        )

    def test_release_asset_url_encodes_names(self) -> None:
        url = release_asset_url("o/r", "tag name", "prompt bundle.zip")
        self.assertTrue(url.endswith("/tag%20name/prompt%20bundle.zip"))

    def test_render_two_and_three_sample_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [sample(index) for index in range(1, 4)]
            for index, item in enumerate(rows, 1):
                image_path = root / f"{index}.png"
                Image.new("RGB", (128 + index, 96 + index), (index * 30, 50, 90)).save(image_path)
                item.extracted_path = str(image_path)
            config = {
                "cell_size": 240,
                "extended_cell_size": 180,
                "header_height": 150,
                "label_height": 58,
                "margin": 16,
                "gap": 8,
                "prompt_max_lines": 2,
            }
            two_path = root / "two.jpg"
            render_card(
                two_path,
                prompt_id="i0001",
                category="product",
                prompt=rows[0].prompt,
                model="model-a",
                cohort_id="cohort",
                samples=rows[:2],
                roles=["Historical", "Latest"],
                config=config,
            )
            three_path = root / "three.jpg"
            render_card(
                three_path,
                prompt_id="i0001",
                category="product",
                prompt=rows[0].prompt,
                model="model-a",
                cohort_id="cohort",
                samples=rows,
                roles=["Earliest", "Historical", "Latest"],
                config=config,
            )
            for path in (two_path, three_path):
                self.assertTrue(path.exists())
                with Image.open(path) as rendered:
                    self.assertGreater(rendered.width, 400)
                    self.assertGreater(rendered.height, 300)

    def test_release_packages_are_zip_only_and_include_full_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for directory in ("primary", "extended", "sidecars", "full"):
                (output / directory).mkdir(parents=True, exist_ok=True)
            (output / "primary" / "primary.jpg").write_bytes(b"primary")
            (output / "extended" / "extended.jpg").write_bytes(b"extended")
            (output / "sidecars" / "sidecar.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            (output / "full" / "i0001-cohort").mkdir(parents=True)
            (output / "full" / "i0001-cohort" / "page.jpg").write_bytes(b"full")
            entry = AtlasEntry(
                "i0001", "product", "prompt", "model-a", "cohort", 9,
                "media-exp-2026-07-09", "primary.jpg", "sidecar.json", "extended.jpg",
                full_files=["i0001-cohort/page.jpg"],
            )
            assets = create_release_packages(output, [entry], {"entries": []}, {"max_release_asset_gib": 0.01})
            self.assertTrue(assets)
            self.assertTrue(all(path.suffix == ".zip" for path in assets))
            bundle = output / "release-assets" / "prompt-i0001-atlas.zip"
            with zipfile.ZipFile(bundle) as archive:
                names = set(archive.namelist())
            self.assertIn("primary/primary.jpg", names)
            self.assertIn("extended/extended.jpg", names)
            self.assertIn("full/i0001-cohort/page.jpg", names)
            self.assertIn("sidecars/sidecar.json", names)


if __name__ == "__main__":
    unittest.main()
