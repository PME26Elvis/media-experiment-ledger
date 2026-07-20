from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from prompt_atlas_core import AtlasEntry
from prompt_atlas_data import command
from prompt_atlas_packages import create_release_packages
from prompt_atlas_video import (
    VideoAtlasEntry,
    VideoSample,
    build_video_entries,
    collect_video_samples,
    extract_videos,
    group_video_candidates,
    probe_video,
    render_video_gif,
    video_cohort_identity,
    video_member_matches,
)

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def make_video(path: Path, hue: int, duration: float = 1.2) -> None:
    command(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x180:rate=12:duration={duration}",
            "-vf",
            f"hue=h={hue}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )


def small_config() -> dict[str, object]:
    return {
        "video_preview_seconds": 1,
        "video_preview_fps": 4,
        "video_gif_colors": 64,
        "video_cell_width": 160,
        "video_cell_height": 90,
        "video_extended_cell_width": 120,
        "video_extended_cell_height": 68,
        "video_header_height": 100,
        "video_label_height": 42,
        "video_margin": 8,
        "video_gap": 6,
        "video_full_page_samples": 16,
        "jpeg_quality": 80,
    }


@unittest.skipUnless(FFMPEG_AVAILABLE, "FFmpeg is required for video Atlas tests")
class PromptAtlasVideoTests(unittest.TestCase):
    def test_member_matching_accepts_harvester_filename(self) -> None:
        self.assertTrue(
            video_member_matches(
                "media/videos/v0001_agnes-task-id.mp4",
                "v0001",
            )
        )
        self.assertFalse(
            video_member_matches(
                "media/images/v0001_agnes-task-id.mp4",
                "v0001",
            )
        )
        self.assertFalse(
            video_member_matches(
                "media/videos/v00010_agnes-task-id.mp4",
                "v0001",
            )
        )

    def test_random_seed_is_evidence_not_cohort_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = []
            roots: dict[str, Path] = {}
            for index, seed in enumerate((111, 222), 1):
                tag = f"media-exp-2026-07-0{index}"
                rows.append(
                    {
                        "tagName": tag,
                        "publishedAt": f"2026-07-0{index}T00:00:00Z",
                    }
                )
                metadata_root = root / tag
                metadata_root.mkdir(parents=True)
                roots[tag] = metadata_root
                record = {
                    "event": "video_completed",
                    "prompt_id": "v0001",
                    "category": "motion",
                    "timestamp": str(index),
                    "finished_at": str(index),
                    "seed": seed,
                    "local_path": "media/videos/v0001_task.mp4",
                    "payload": {
                        "model": "agnes-video-v2.0",
                        "prompt": "moving cube",
                        "num_frames": 24,
                        "frame_rate": 12,
                        "seed": seed,
                    },
                }
                (metadata_root / f"run_{index}-outputs.jsonl").write_text(
                    json.dumps(record) + "\n",
                    encoding="utf-8",
                )
            samples = collect_video_samples(rows, roots)
            self.assertEqual(len(samples), 2)
            self.assertEqual(samples[0].cohort_id, samples[1].cohort_id)
            self.assertNotEqual(samples[0].seed, samples[1].seed)
            self.assertNotIn("seed", samples[0].settings)
            self.assertEqual(len(group_video_candidates(samples)), 1)

    def test_probe_and_render_synchronized_gif(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            samples: list[VideoSample] = []
            for index, hue in enumerate((0, 120), 1):
                path = root / f"sample-{index}.mp4"
                make_video(path, hue)
                metadata = probe_video(path)
                samples.append(
                    VideoSample(
                        "v0001",
                        "motion",
                        "moving cube",
                        "model-a",
                        {"model": "model-a", "frame_rate": 12},
                        video_cohort_identity(
                            "v0001",
                            "model-a",
                            {"model": "model-a", "frame_rate": 12},
                        ),
                        f"media-exp-2026-07-0{index}",
                        "",
                        f"run_{index}",
                        str(index),
                        str(index),
                        str(path),
                        seed=index,
                        extracted_path=str(path),
                        sha256=str(index),
                        **metadata,
                    )
                )
            destination = root / "comparison.gif"
            render_video_gif(
                destination,
                prompt_id="v0001",
                category="motion",
                prompt="moving cube",
                model="model-a",
                cohort_id=samples[0].cohort_id,
                samples=samples,
                roles=["Historical", "Latest"],
                config=small_config(),
            )
            self.assertTrue(destination.exists())
            self.assertGreater(destination.stat().st_size, 1000)
            with Image.open(destination) as rendered:
                self.assertGreater(getattr(rendered, "n_frames", 1), 1)
                self.assertGreater(rendered.width, 300)
                self.assertGreater(rendered.height, 150)

    def test_release_style_archives_build_complete_video_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = []
            metadata_roots: dict[str, Path] = {}
            archive_roots: dict[str, Path] = {}
            for index, hue in enumerate((0, 120), 1):
                tag = f"media-exp-2026-07-0{index}"
                rows.append(
                    {
                        "tagName": tag,
                        "publishedAt": f"2026-07-0{index}T00:00:00Z",
                    }
                )
                metadata_root = root / "metadata" / tag
                metadata_root.mkdir(parents=True)
                metadata_roots[tag] = metadata_root
                archive_root = root / "archives" / tag
                archive_root.mkdir(parents=True)
                archive_roots[tag] = archive_root
                run_id = f"run_{index}"
                source_video = root / f"{run_id}.mp4"
                make_video(source_video, hue)
                record = {
                    "event": "video_completed",
                    "phase": "video",
                    "prompt_id": "v0001",
                    "category": "motion",
                    "timestamp": str(index),
                    "finished_at": str(index),
                    "seed": index,
                    "local_path": "media/videos/v0001_task.mp4",
                    "payload": {
                        "model": "agnes-video-v2.0",
                        "prompt": "moving cube",
                        "num_frames": 24,
                        "frame_rate": 12,
                        "seed": index,
                    },
                }
                (metadata_root / f"{run_id}-outputs.jsonl").write_text(
                    json.dumps(record) + "\n",
                    encoding="utf-8",
                )
                with zipfile.ZipFile(
                    archive_root / f"{run_id}-videos.zip",
                    "w",
                ) as archive:
                    archive.write(
                        source_video,
                        "media/videos/v0001_task.mp4",
                    )

            samples = collect_video_samples(rows, metadata_roots)
            groups = group_video_candidates(samples)
            extract_videos(groups, archive_roots, root / "extracted")
            self.assertTrue(all(sample.sha256 for sample in samples))

            entries, missing, metadata_count, candidate_count = build_video_entries(
                rows,
                metadata_roots,
                "f" * 64,
                root / "work",
                root / "output",
                small_config(),
                rows[-1]["tagName"],
                archive_roots=archive_roots,
            )
            self.assertEqual(metadata_count, 2)
            self.assertEqual(candidate_count, 1)
            self.assertFalse(missing)
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry.media_type, "video")
            self.assertTrue(
                (root / "output" / "video" / "primary" / entry.primary_file).exists()
            )
            self.assertTrue(
                (root / "output" / "video" / "sidecars" / entry.sidecar_file).exists()
            )
            self.assertEqual(len(entry.full_files), 1)
            self.assertTrue(
                (
                    root
                    / "output"
                    / "video"
                    / "keyframes"
                    / entry.full_files[0]
                ).exists()
            )

    def test_release_packages_include_image_and_video_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for directory in (
                "primary",
                "sidecars",
                "full/i0001-cohort",
                "video/primary",
                "video/sidecars",
                "video/keyframes/v0001-cohort",
            ):
                (output / directory).mkdir(parents=True, exist_ok=True)
            (output / "primary" / "image.jpg").write_bytes(b"image")
            (output / "sidecars" / "image.json").write_text("{}")
            (output / "full" / "i0001-cohort" / "page.jpg").write_bytes(b"page")
            (output / "video" / "primary" / "video.gif").write_bytes(b"GIF89a")
            (output / "video" / "sidecars" / "video.json").write_text("{}")
            (
                output
                / "video"
                / "keyframes"
                / "v0001-cohort"
                / "page.jpg"
            ).write_bytes(b"page")

            image_entry = AtlasEntry(
                "i0001",
                "product",
                "image prompt",
                "image-model",
                "i0001-cohort",
                2,
                "media-exp-2026-07-01",
                "image.jpg",
                "image.json",
                None,
                full_files=["i0001-cohort/page.jpg"],
            )
            video_entry = VideoAtlasEntry(
                "v0001",
                "motion",
                "video prompt",
                "video-model",
                "v0001-cohort",
                2,
                "media-exp-2026-07-01",
                "video.gif",
                "video.json",
                None,
                full_files=["v0001-cohort/page.jpg"],
            )
            report: dict[str, object] = {}
            assets = create_release_packages(
                output,
                [image_entry, video_entry],
                report,
                {
                    "max_release_asset_gib": 0.01,
                    "prompts_per_bundle": 15,
                    "video_prompts_per_bundle": 15,
                },
            )
            self.assertTrue(all(path.suffix == ".zip" for path in assets))
            self.assertEqual(report["prompt_bundle_count"], 1)
            self.assertEqual(report["video_prompt_bundle_count"], 1)
            video_bundle = next(
                path
                for path in assets
                if path.name.startswith("video-atlas-bundle-")
            )
            with zipfile.ZipFile(video_bundle) as archive:
                names = set(archive.namelist())
            self.assertIn("video/primary/video.gif", names)
            self.assertIn("video/sidecars/video.json", names)
            self.assertIn(
                "video/keyframes/v0001-cohort/page.jpg",
                names,
            )
            self.assertIn(
                "video-bundle-manifests/video-prompt-bundle-001.json",
                names,
            )


if __name__ == "__main__":
    unittest.main()
