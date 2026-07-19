import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "publish_results",
    Path(__file__).parents[1] / "tools" / "publish_results.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class PublishResultsTests(unittest.TestCase):
    def test_plan_run_packages_metadata_and_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run_20260629_120000"
            (run / "media" / "images").mkdir(parents=True)
            (run / "media" / "videos").mkdir(parents=True)
            (run / "outputs.jsonl").write_text(
                json.dumps(
                    {
                        "event": "image_completed",
                        "category": "product",
                        "payload": {"model": "m1"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run / "errors.jsonl").write_text("", encoding="utf-8")
            (run / "media" / "images" / "i1.png").write_bytes(b"image")
            (run / "media" / "videos" / "v1.mp4").write_bytes(b"video")
            staging = root / "staging"
            staging.mkdir()

            plan = mod.plan_run(run, staging, 1024)
            names = {asset.name for asset in plan.assets}
            self.assertIn("run_20260629_120000-images.zip", names)
            self.assertIn("run_20260629_120000-videos.zip", names)
            self.assertIn("run_20260629_120000-outputs.jsonl", names)
            images_zip = next(asset.path for asset in plan.assets if asset.name.endswith("-images.zip"))
            videos_zip = next(asset.path for asset in plan.assets if asset.name.endswith("-videos.zip"))
            for archive_path in (images_zip, videos_zip):
                with zipfile.ZipFile(archive_path) as archive:
                    members = set(archive.namelist())
                self.assertIn("outputs.jsonl", members)
                self.assertIn("errors.jsonl", members)
            self.assertEqual(plan.stats["image_completed"], 1)
            self.assertEqual(plan.stats["file_count"], 4)
            self.assertTrue(plan.digest)

    def test_split_files_respects_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for index in range(3):
                path = root / f"{index}.bin"
                path.write_bytes(b"x" * 6)
                files.append(path)
            parts = mod.split_files(files, 10)
            self.assertEqual([len(part) for part in parts], [1, 1, 1])

    def test_batch_dispatch_targets_full_corpus_workflow_once(self):
        tags = ["media-exp-2026-07-01", "media-exp-2026-07-02"]
        with patch.object(mod, "atlas_batch_id", return_value="batch-fixed"):
            command = mod.atlas_dispatch_command("owner/repo", tags)
        self.assertEqual(command.count("visual-analysis.yml"), 1)
        self.assertIn("batch_id=batch-fixed", command)
        self.assertIn("force=false", command)
        self.assertNotIn(tags[0], command)
        self.assertNotIn(tags[1], command)

    def test_published_message_extracts_release_tag(self):
        message = (
            "PUBLISHED 2026-07-02: media-exp-2026-07-02-s01 "
            "(2 new run(s), 6 asset(s))"
        )
        match = mod.PUBLISHED_TAG_RE.match(message)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "media-exp-2026-07-02-s01")


if __name__ == "__main__":
    unittest.main()
