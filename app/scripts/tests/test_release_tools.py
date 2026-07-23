from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
APP_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = APP_ROOT.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from collect_platform_artifacts import collect_platform_artifacts  # noqa: E402
from finalize_release_assets import evidence_bundle_name, finalize  # noqa: E402
from render_release_notes import render  # noqa: E402
from resolve_release_plan import build_plan, resolve_version  # noqa: E402
from verify_public_release import verify_public  # noqa: E402
from verify_release_assets import (  # noqa: E402
    expected_evidence_names,
    expected_package_names,
    verify,
)


def plan(version: str = '0.1.0-beta.2') -> dict[str, object]:
    return {
        'version': version,
        'channel': 'beta',
        'tag': f'studio-v{version}',
        'source_sha': 'c' * 40,
        'source_branch': 'app-main',
        'release_date_taipei': '2026-07-23',
        'generated_at_utc': '2026-07-23T03:40:00Z',
    }


def write_raw_release(root: Path, release_plan: dict[str, object]) -> None:
    for name in expected_package_names(str(release_plan['version'])):
        (root / name).write_bytes(b'x')
    for name in expected_evidence_names():
        if name.endswith('packaged-smoke-evidence.json'):
            payload = {
                'packaged': True,
                'rendererLoaded': True,
                'preloadBridge': True,
                'engineReady': True,
                'database': {'ok': True},
            }
        else:
            payload = {'name': name}
        (root / name).write_text(json.dumps(payload), encoding='utf-8')
    (root / 'RELEASE_NOTES.md').write_text('# Beta notes\n', encoding='utf-8')


class ReleasePlanTests(unittest.TestCase):
    def test_auto_beta_version_increments_without_clobbering(self) -> None:
        release_plan = build_plan(
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
        self.assertEqual(release_plan['version'], '0.1.0-beta.3')
        self.assertEqual(release_plan['tag'], 'studio-v0.1.0-beta.3')
        self.assertEqual(release_plan['release_date_taipei'], '2026-07-23')
        self.assertEqual(release_plan['features'], ['First feature', 'Second feature'])
        self.assertTrue(release_plan['publish'])
        self.assertFalse(release_plan['draft'])

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
            'version': '0.1.0-beta.2',
            'channel': 'beta',
            'release_date_taipei': '2026-07-23',
            'source_sha': 'b' * 40,
            'features': 'clean assets, fix packaging\nadd release evidence',
            'release_notes': 'Clean public beta build.',
        })
        self.assertIn('- clean assets', text)
        self.assertIn('- fix packaging', text)
        self.assertIn('Taipei date: **2026-07-23**', text)
        self.assertIn('may show an', text)
        self.assertIn('when signing keys are configured', text)
        self.assertNotIn('signed checksum file', text)

    def test_prerelease_steps_do_not_receive_signing_secret_paths(self) -> None:
        workflow = (REPOSITORY_ROOT / '.github/workflows/app-release-core.yml').read_text(
            encoding='utf-8'
        )
        unsigned_windows = workflow.split(
            'Build unsigned Windows prerelease packages', 1
        )[1].split('Build signed Windows stable packages', 1)[0]
        unsigned_macos = workflow.split(
            'Build unsigned macOS prerelease packages', 1
        )[1].split('Build signed and notarized macOS stable packages', 1)[0]
        self.assertNotIn('WIN_CSC_LINK', unsigned_windows)
        self.assertNotIn('MAC_CSC_LINK', unsigned_macos)
        self.assertNotIn('APPLE_ID', unsigned_macos)
        self.assertIn("CSC_IDENTITY_AUTO_DISCOVERY: 'false'", unsigned_windows)
        self.assertIn("CSC_IDENTITY_AUTO_DISCOVERY: 'false'", unsigned_macos)

    def test_linux_package_metadata_is_complete(self) -> None:
        package = json.loads((APP_ROOT / 'package.json').read_text(encoding='utf-8'))
        self.assertTrue(package['homepage'].startswith('https://github.com/'))
        self.assertIn('@', package['author']['email'])
        linux = package['build']['linux']
        self.assertIn('@', linux['maintainer'])
        self.assertTrue(linux['syncDesktopName'])
        self.assertEqual(package['desktopName'], 'Media Experiment Ledger Studio')


class ReleaseAssetTests(unittest.TestCase):
    def test_collector_ignores_recursive_runtime_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_root = Path(directory)
            release = app_root / 'release'
            release.mkdir()
            package_name = 'Media-Experiment-Ledger-Studio-0.1.0-beta.2-windows-x64-setup.exe'
            (release / package_name).write_bytes(b'package')
            (release / 'latest.yml').write_text('version: beta.2', encoding='utf-8')
            unpacked = release / 'win-unpacked' / 'resources' / 'engine-bin'
            unpacked.mkdir(parents=True)
            (unpacked / 'base_library.zip').write_bytes(b'internal')
            (unpacked / 'mel-engine.exe').write_bytes(b'internal')

            evidence_root = app_root / 'release-evidence'
            evidence_root.mkdir()
            for name in ('sbom.cdx.json', 'third-party-notices.json', 'build-input-manifest.json'):
                (evidence_root / name).write_text('{}', encoding='utf-8')
            (app_root / 'packaged-smoke-evidence.json').write_text('{}', encoding='utf-8')
            engine = app_root / 'engine-bin' / 'mel-engine'
            engine.mkdir(parents=True)
            (engine / 'engine-build-manifest.json').write_text('{}', encoding='utf-8')

            collected = collect_platform_artifacts(app_root, 'windows-x64')
            self.assertIn(package_name, collected)
            self.assertIn('windows-x64-latest.yml', collected)
            self.assertNotIn('base_library.zip', collected)
            self.assertNotIn('mel-engine.exe', collected)
            self.assertFalse((app_root / 'artifact-out' / 'base_library.zip').exists())

    def test_exact_raw_matrix_becomes_clean_public_release(self) -> None:
        release_plan = plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_raw_release(root, release_plan)
            raw = verify(root, release_plan, minimum_package_bytes=1)
            self.assertEqual(raw['package_count'], 8)
            self.assertEqual(raw['evidence_count'], 24)
            self.assertTrue(raw['unexpected_assets_blocked'])

            manifest = finalize(root, release_plan, minimum_package_bytes=1)
            self.assertEqual(manifest['schema_version'], 3)
            self.assertEqual(manifest['source_sha'], 'c' * 40)
            self.assertEqual(manifest['public_asset_policy'], 'eight_packages_plus_consolidated_evidence')

            bundle = root / evidence_bundle_name(str(release_plan['version']))
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(set(archive.namelist()), set(expected_evidence_names()))

            result = verify_public(root, release_plan)
            self.assertTrue(result['clean_public_asset_set'])
            self.assertEqual(result['public_asset_count'], 13)
            self.assertEqual(result['checksummed_asset_count'], 11)
            self.assertEqual(result['evidence_member_count'], 24)
            self.assertEqual(
                {path.name for path in root.iterdir() if path.is_file()},
                set(expected_package_names(str(release_plan['version']))) | {
                    evidence_bundle_name(str(release_plan['version'])),
                    'RELEASE_NOTES.md',
                    'release-verification.json',
                    'release-manifest.json',
                    'SHA256SUMS',
                },
            )

    def test_unexpected_runtime_file_is_release_blocking(self) -> None:
        release_plan = plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_raw_release(root, release_plan)
            (root / 'base_library.zip').write_bytes(b'internal runtime')
            with self.assertRaisesRegex(RuntimeError, 'Unexpected pre-publication assets'):
                verify(root, release_plan, minimum_package_bytes=1)

    def test_missing_architecture_is_release_blocking(self) -> None:
        release_plan = plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'RELEASE_NOTES.md').write_text('notes', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'Missing required Studio release assets'):
                verify(root, release_plan, minimum_package_bytes=1)


if __name__ == '__main__':
    unittest.main()
