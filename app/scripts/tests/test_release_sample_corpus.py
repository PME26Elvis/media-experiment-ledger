from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'studio-sample-corpus.yml'
REQUEST = REPO_ROOT / '.github' / 'studio-sample-corpus-request.json'


class SampleCorpusReleaseWorkflowTests(unittest.TestCase):
    def test_publication_is_draft_first_and_never_clobbers(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertNotIn('--clobber', text)
        self.assertNotIn('Create or update corpus Release', text)
        self.assertIn('Reject an existing corpus tag or Release', text)
        self.assertIn('Refusing to overwrite existing tag', text)
        self.assertIn('Create immutable draft and upload exact assets', text)
        self.assertIn('--draft', text)
        self.assertIn('remote asset set mismatch', text)
        self.assertIn('Publish verified corpus Release once', text)
        self.assertIn('-F draft=false', text)

    def test_request_file_is_safe_by_default(self) -> None:
        request = json.loads(REQUEST.read_text(encoding='utf-8'))
        self.assertEqual(request['schema_version'], 1)
        self.assertFalse(request['enabled'])
        self.assertEqual(request['tier'], 'quick-start')
        self.assertEqual(request['source_release_tags'], '')
        self.assertTrue(request['draft'])

    def test_push_trigger_is_narrow_and_source_sha_is_pinned(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("branches: [app-main]", text)
        self.assertIn("'.github/studio-sample-corpus-request.json'", text)
        self.assertIn('does not match the pre-trigger app-main SHA', text)
        self.assertIn('--target "$REQUEST_SOURCE_SHA"', text)
        self.assertIn("EVENT_BEFORE: ${{ github.event.before || '' }}", text)


if __name__ == '__main__':
    unittest.main()
