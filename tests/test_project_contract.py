from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_project_contract import validate


class ProjectContractTests(unittest.TestCase):
    def test_all_contract_surfaces_are_synchronized(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
