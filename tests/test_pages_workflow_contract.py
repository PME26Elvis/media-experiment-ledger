from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PagesWorkflowContractTests(unittest.TestCase):
    def test_pages_deploy_is_independent_from_git_writeback(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "analytics.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  build:", workflow)
        self.assertIn("  deploy:", workflow)
        self.assertIn("  writeback:", workflow)
        self.assertGreaterEqual(workflow.count("needs: build"), 2)
        self.assertIn("actions/upload-pages-artifact@v3", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("actions/download-artifact@v5", workflow)
        self.assertIn("analytics-writeback-${{ github.run_id }}", workflow)
        self.assertIn("paths=(analytics forecasts)", workflow)
        self.assertIn("git rebase origin/main", workflow)
        self.assertNotIn("git add analytics forecasts site", workflow)
        self.assertNotIn("git status --porcelain -- analytics forecasts site", workflow)

    def test_compiled_site_is_ignored_and_not_a_writeback_path(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("site/", ignored)
        workflow = (ROOT / ".github" / "workflows" / "analytics.yml").read_text(
            encoding="utf-8"
        )
        writeback = workflow.split("  writeback:", 1)[1]
        self.assertNotIn("git add site", writeback)
        self.assertNotIn("site/", writeback)

    def test_atlas_release_note_contract_remains_unchanged(self) -> None:
        import json

        config = json.loads(
            (ROOT / "visual-analysis" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["release_notes_image_highlights"], 15)
        self.assertEqual(config["release_notes_image_min_samples"], 4)
        self.assertEqual(config["release_notes_video_highlights"], "all")
        self.assertEqual(config["release_notes_video_min_samples"], 2)
        self.assertEqual(config["prompts_per_bundle"], 15)
        self.assertEqual(config["video_prompts_per_bundle"], 15)


if __name__ == "__main__":
    unittest.main()
