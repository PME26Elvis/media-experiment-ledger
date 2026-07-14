import importlib.util
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


archive_mod = load_module("publish_from_archive", ROOT / "tools" / "publish_from_archive.py")
snapshot_mod = load_module("input_snapshot", ROOT / "tools" / "input_snapshot.py")


class ArchiveIngestTests(unittest.TestCase):
    def test_extracts_top_level_results_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "results.zip"
            with zipfile.ZipFile(archive_path, "w", allowZip64=True) as archive:
                archive.writestr("results/2026-06-29/run_20260629_120000/outputs.jsonl", "{}\n")
                archive.writestr("results/2026-06-29/run_20260629_120000/errors.jsonl", "")
                archive.writestr("results/2026-06-29/run_20260629_120000/media/videos/v1.mp4", b"video")
            inspection = archive_mod.inspect_archive(archive_path)
            self.assertEqual(inspection.file_count, 3)
            destination = root / "extracted"
            archive_mod.safe_extract(archive_path, destination)
            detected = archive_mod.find_results_root(destination)
            self.assertEqual(detected, destination / "results")
            self.assertTrue((detected / "2026-06-29" / "run_20260629_120000" / "media" / "videos" / "v1.mp4").exists())

    def test_accepts_one_wrapper_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "batch.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("export/results/2026-06-30/run_test/outputs.jsonl", "{}\n")
            destination = root / "extracted"
            archive_mod.safe_extract(archive_path, destination)
            self.assertEqual(archive_mod.find_results_root(destination), destination / "export" / "results")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", "no")
            with self.assertRaises(archive_mod.ArchiveInputError):
                archive_mod.inspect_archive(archive_path)


class InputSnapshotTests(unittest.TestCase):
    def test_split_and_restore_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "results.zip"
            payload = b"0123456789abcdefghijklmnopqrstuvwxyz"
            source.write_bytes(payload)
            parts_dir = root / "parts"
            records, digest, size = snapshot_mod.split_archive(source, parts_dir, 10)
            self.assertEqual([record.size_bytes for record in records], [10, 10, 10, 6])
            tag = snapshot_mod.snapshot_tag(digest, datetime(2026, 7, 15, 23, 0, tzinfo=ZoneInfo("Asia/Taipei")))
            manifest = snapshot_mod.make_manifest(source, records, digest, size, tag)
            output = root / "restored.zip"
            snapshot_mod.restore_from_directory(manifest, parts_dir, output)
            self.assertEqual(output.read_bytes(), payload)
            self.assertEqual(tag, f"media-input-2026-07-15-{digest[:12]}")

    def test_split_rejects_release_boundary_or_larger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "results.zip"
            source.write_bytes(b"data")
            with self.assertRaises(ValueError):
                snapshot_mod.split_archive(source, root / "parts", 2 * 1024**3)

    def test_restore_detects_modified_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "results.zip"
            source.write_bytes(b"abcdefghijk")
            parts_dir = root / "parts"
            records, digest, size = snapshot_mod.split_archive(source, parts_dir, 5)
            manifest = snapshot_mod.make_manifest(source, records, digest, size, "media-input-test")
            (parts_dir / records[0].name).write_bytes(b"xxxxx")
            with self.assertRaises(snapshot_mod.SnapshotError):
                snapshot_mod.restore_from_directory(manifest, parts_dir, root / "restored.zip")

    @mock.patch.object(snapshot_mod, "list_snapshot_tags")
    def test_latest_resolves_to_newest_snapshot(self, list_tags):
        list_tags.return_value = [
            "media-input-2026-07-16-newest000001",
            "media-input-2026-07-15-older0000002",
        ]
        self.assertEqual(
            snapshot_mod.resolve_snapshot_tag("latest"),
            "media-input-2026-07-16-newest000001",
        )

    @mock.patch.object(snapshot_mod, "list_snapshot_tags")
    def test_missing_example_tag_falls_back_when_only_one_snapshot_exists(self, list_tags):
        list_tags.return_value = ["media-input-2026-07-15-real12345678"]
        self.assertEqual(
            snapshot_mod.resolve_snapshot_tag("media-input-2026-07-15-a1b2c3d4e5f6"),
            "media-input-2026-07-15-real12345678",
        )

    @mock.patch.object(snapshot_mod, "list_snapshot_tags")
    def test_missing_tag_lists_choices_when_multiple_snapshots_exist(self, list_tags):
        list_tags.return_value = [
            "media-input-2026-07-16-newest000001",
            "media-input-2026-07-15-older0000002",
        ]
        with self.assertRaisesRegex(snapshot_mod.SnapshotError, "Available input snapshot tags"):
            snapshot_mod.resolve_snapshot_tag("media-input-does-not-exist")


if __name__ == "__main__":
    unittest.main()
