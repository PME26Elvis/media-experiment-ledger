from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from tools.yolo_corpus import build_inventory, safe_member


class YoloCorpusTests(unittest.TestCase):
    def test_safe_member_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            safe_member("../../secret.png")
        self.assertEqual(
            safe_member("media/images/i0001_a.png").as_posix(),
            "media/images/i0001_a.png",
        )

    def test_inventory_deduplicates_bytes_and_keeps_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            releases = []
            roots = {}
            image_path = root / "source.png"
            Image.new("RGB", (32, 16), "red").save(image_path)
            data = image_path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            for index, date in enumerate(("2026-07-01", "2026-07-02"), 1):
                tag = f"media-exp-{date}"
                releases.append(
                    {"tagName": tag, "publishedAt": f"{date}T00:00:00Z"}
                )
                release_root = root / tag
                release_root.mkdir()
                run_id = f"run_2026070{index}_000000"
                asset_name = f"{run_id}-images.zip"
                with zipfile.ZipFile(release_root / asset_name, "w") as archive:
                    archive.writestr("media/images/i0001_same.png", data)
                asset_bytes = (release_root / asset_name).read_bytes()
                manifest = {
                    "experiment_date_taipei": date,
                    "content_digest": str(index),
                    "runs": [
                        {
                            "run_id": run_id,
                            "files": [
                                {
                                    "path": "media/images/i0001_same.png",
                                    "size_bytes": len(data),
                                    "sha256": digest,
                                }
                            ],
                            "assets": [
                                {
                                    "name": asset_name,
                                    "kind": "images",
                                    "size_bytes": len(asset_bytes),
                                    "sha256": hashlib.sha256(asset_bytes).hexdigest(),
                                }
                            ],
                        }
                    ],
                }
                (release_root / f"manifest-{date}.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
                (release_root / f"{run_id}-outputs.jsonl").write_text(
                    json.dumps(
                        {
                            "event": "image_completed",
                            "prompt_id": "i0001",
                            "category": "test",
                            "local_path": "media/images/i0001_same.png",
                            "payload": {"model": "test", "prompt": "red"},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                roots[tag] = release_root
            inventory = build_inventory(releases, roots, root / "extract")
            self.assertEqual(inventory.source_file_count, 2)
            self.assertEqual(len(inventory.images), 1)
            self.assertEqual(len(inventory.images[0].aliases), 2)


if __name__ == "__main__":
    unittest.main()
