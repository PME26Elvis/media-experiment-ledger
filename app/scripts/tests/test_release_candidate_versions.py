from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'resolve_release_plan.py'
SPEC = importlib.util.spec_from_file_location('resolve_release_plan', SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseCandidateVersionTests(unittest.TestCase):
    def test_beta_distribution_accepts_beta_and_rc_versions(self) -> None:
        MODULE.validate_explicit_version('1.0.0-beta.3', 'beta')
        MODULE.validate_explicit_version('1.0.0-rc.1', 'beta')

    def test_beta_distribution_rejects_unrelated_prerelease_labels(self) -> None:
        with self.assertRaisesRegex(ValueError, 'beta distribution accepts'):
            MODULE.validate_explicit_version('1.0.0-preview.1', 'beta')

    def test_alpha_and_stable_constraints_remain_strict(self) -> None:
        MODULE.validate_explicit_version('1.0.0-alpha.2', 'alpha')
        MODULE.validate_explicit_version('1.0.0', 'stable')
        with self.assertRaises(ValueError):
            MODULE.validate_explicit_version('1.0.0-rc.1', 'stable')
        with self.assertRaises(ValueError):
            MODULE.validate_explicit_version('1.0.0-rc.1', 'alpha')

    def test_rc_request_resolves_to_prerelease_without_publishing_override(self) -> None:
        plan = MODULE.build_plan(
            {
                'schema_version': 1,
                'version': '1.0.0-rc.2',
                'channel': 'beta',
                'draft': False,
                'publish': True,
            },
            package_version='0.1.0',
            existing_tags=set(),
            source_sha='a' * 40,
            overrides={'draft': 'true', 'publish': 'false'},
        )
        self.assertEqual(plan['tag'], 'studio-v1.0.0-rc.2')
        self.assertTrue(plan['prerelease'])
        self.assertTrue(plan['draft'])
        self.assertFalse(plan['publish'])


if __name__ == '__main__':
    unittest.main()
