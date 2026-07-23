from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from finalize_release_assets import finalize  # noqa: E402
from render_release_notes import render  # noqa: E402
from resolve_release_plan import build_plan, resolve_version  # noqa: E402
from verify_release_assets import (  # noqa: E402
    expected_evidence_names,
    expected_package_names,
    verify,
)


class ReleasePlanTests(unittest.TestCase):
    def test_auto_beta_version_increments_without_clobbering(self) -> None:
        plan = build_plan(
            {
                'schema_version': 1,
                'version': 'auto',
                'channel': 'beta',
                'draft': False,
                'publish': True,
                'features': ['First feature', 'Second feature', 'First feature'],
            },
            package_version='0.1.0',
            existing_tags={'studio-v0.1.0-beta.1', 'studio-v0.1.0-beta.2'},
            source_sha='a' * 40,
            now=datetime(2026, 7, 22, 18, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(plan['version'], '0.1.0-beta.3')
        self.assertEqual(plan['tag'], 'studio-v0.1.0-beta.3')
        self.assertEqual(plan['release_date_taipei'], '2026-07-23')
        self.assertEqual(plan['features'], ['First feature', 'Second feature'])
        self.assertTrue(plan['publish'])
        self.assertFalse(plan['draft'])

    def test_explicit_collision_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, 'will not be modified'):
            resolve_version(
                '0.1.0-beta.1',
                channel='beta',
                package_version='0.1.0',
                existing_tags={'studio-v0.1.0-beta.1'},
            )

    def test_channel_and_prerelease_suffix_must_match(self) -> None:
        with self.assertRaisesRegex(ValueError, 'matching -beta'):
            resolve_version(
                '0.1.0',
                channel='beta',
                package_version='0.1.0',
                existing_tags=set(),
            )

    def test_release_notes_are_truthful_for_unsigned_prerelease(self) -> None:
        text = render({
            'version': '0.1.0-beta.1',
            'channel': 'beta',
            'release_date_taipei': '2026-07-23',
            'source_sha': 'b' * 40,
            'features': 'add language, fix packaging\nadd release entry',
            'release_notes': 'First public validation build.',
        })
        self.assertIn('- add language', text)
        self.assertIn('- fix packaging', text)
        self.assertIn('Taipei date: **2026-07-23**', text)
        self.assertIn('may show an', text)
        self.assertIn('when signing keys are configured', text)
        self.assertNotIn('signed checksum file', text)


class ReleaseAssetTests(unittest.TestCase):
    def test_exact_package_and_evidence_matrix(self) -> None:
        plan = {
            'version': '0.1.0-beta.1',
            'channel': 'beta',
            'tag': 'studio-v0.1.0-beta.1',
            'source_sha': 'c' * 40,
            'source_branch': 'app-main',
            'release_date_taipei': '2026-07-23',
            'generated_at_utc': '2026-07-22T18:30:00Z',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in expected_package_names(plan['version']):
                (root / name).write_bytes(b'x')
            for name in expected_evidence_names():
                if name.endswith('packaged-smoke-evidence.json'):
                    (root / name).write_text(json.dumps({
                        'packaged': True,
                        'rendererLoaded': True,
                        'preloadBridge': True,
                        'engineReady': True,
                        'database': {'ok': True},
                    }), encoding='utf-8')
                else:
                    (root / name).write_text('{}', encoding='utf-8')
            (root / 'SBOM.cdx.json').write_text('{}', encoding='utf-8')
            result = verify(root, plan, minimum_package_bytes=1)
            self.assertEqual(result['package_count'], 8)
            self.assertEqual(result['evidence_count'], 8)
            manifest = finalize(root, plan)
            self.assertEqual(manifest['schema_version'], 2)
            self.assertEqual(manifest['source_sha'], 'c' * 40)
            self.assertEqual(manifest['release_date_taipei'], '2026-07-23')
            self.assertTrue((root / 'SHA256SUMS').is_file())
            self.assertTrue((root / 'release-manifest.json').is_file())

    def test_missing_architecture_is_release_blocking(self) -> None:
        plan = {'version': '0.1.0-beta.1'}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'Missing required Studio release assets'):
                verify(Path(directory), plan, minimum_package_bytes=1)


if __name__ == '__main__':
    unittest.main()
