from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'app-release.yml'


class ReleaseRequestPreflightTests(unittest.TestCase):
    def test_release_request_pull_requests_run_without_publishing(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('pull_request:', text)
        self.assertIn('- app/release-request.json', text)
        self.assertIn("github.event.pull_request.head.sha", text)
        self.assertIn("github.event_name == 'pull_request' && 'false'", text)
        self.assertIn("github.event_name == 'pull_request' && 'true'", text)

    def test_real_push_release_behavior_remains_enabled(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('push:', text)
        self.assertIn("github.event_name == 'push' && github.sha", text)
        self.assertIn('secrets: inherit', text)


if __name__ == '__main__':
    unittest.main()
