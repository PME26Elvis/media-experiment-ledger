from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_site_build import BASE, DATA_ARTIFACTS, PRIMARY_ROUTES, validate


class ValidateSiteBuildTests(unittest.TestCase):
    def build_fixture(self, root: Path) -> None:
        links = "".join(f'<a href="{BASE}{route}/">{route}</a>' for route in PRIMARY_ROUTES)
        for route in PRIMARY_ROUTES:
            path = root / route / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            attributes = ""
            for _, relative, data_route, attribute in DATA_ARTIFACTS:
                if route == data_route:
                    attributes += f' {attribute}="{BASE}{relative.as_posix()}"'
            body = links if route == "overview" else route
            path.write_text(f"<html><body{attributes}>{body}</body></html>", encoding="utf-8")
        for _, relative, _, _ in DATA_ARTIFACTS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"ok": True}), encoding="utf-8")

    def test_complete_pages_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.build_fixture(root)
            validate(root)

    def test_missing_yolo_index_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.build_fixture(root)
            (root / "data" / "yolo" / "latest.json").unlink()
            with self.assertRaises(SystemExit) as context:
                validate(root)
            self.assertIn("data/yolo/latest.json", str(context.exception))

    def test_missing_visual_lab_route_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.build_fixture(root)
            (root / "visual-lab" / "index.html").unlink()
            with self.assertRaises(SystemExit) as context:
                validate(root)
            self.assertIn("visual-lab", str(context.exception))


if __name__ == "__main__":
    unittest.main()
