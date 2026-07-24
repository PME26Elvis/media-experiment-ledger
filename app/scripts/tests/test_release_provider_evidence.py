from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'enforce_provider_evidence.py'
SPEC = importlib.util.spec_from_file_location('enforce_provider_evidence', SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProviderEvidenceEnforcementTests(unittest.TestCase):
    def test_accepts_real_node_assignment_and_matching_packaged_inventory(self) -> None:
        failures = MODULE.enforce(
            provider_key='directml',
            qualification_outcome='success',
            evidence={
                'provider': 'DmlExecutionProvider',
                'available': True,
                'status': 'executed',
                'passed': True,
                'comparison': {'passed': True},
                'target': {'assigned_node_count': 17},
            },
            manifest={'provider_inventory': {'available_providers': ['DmlExecutionProvider', 'CPUExecutionProvider']}},
        )
        self.assertEqual(failures, [])

    def test_inventory_mode_accepts_truthful_cpu_fallback_probe(self) -> None:
        failures = MODULE.enforce(
            provider_key='directml',
            qualification_outcome='failure',
            mode='inventory',
            evidence={
                'provider': 'DmlExecutionProvider',
                'available': True,
                'status': 'executed',
                'passed': False,
                'comparison': {'passed': True},
                'target': {
                    'assigned_node_count': 0,
                    'session_providers': ['CPUExecutionProvider'],
                },
            },
            manifest={'provider_inventory': {'available_providers': ['DmlExecutionProvider', 'CPUExecutionProvider']}},
        )
        self.assertEqual(failures, [])

    def test_inventory_mode_rejects_missing_runtime_or_broken_probe(self) -> None:
        failures = MODULE.enforce(
            provider_key='directml',
            qualification_outcome='failure',
            mode='inventory',
            evidence={
                'provider': 'DmlExecutionProvider',
                'available': False,
                'status': 'error',
                'passed': False,
                'error': {'message': 'failed'},
            },
            manifest={'provider_inventory': {'available_providers': ['CPUExecutionProvider']}},
        )
        self.assertTrue(any('missing qualified provider' in item for item in failures))
        self.assertTrue(any('did not expose' in item for item in failures))
        self.assertTrue(any('did not execute a comparison' in item for item in failures))

    def test_execution_mode_rejects_fallback_only_or_failed_evidence(self) -> None:
        failures = MODULE.enforce(
            provider_key='coreml',
            qualification_outcome='failure',
            evidence={
                'provider': 'CoreMLExecutionProvider',
                'available': False,
                'status': 'error',
                'passed': False,
                'target': {'assigned_node_count': 0},
                'error': {'message': 'failed'},
            },
            manifest={'provider_inventory': {'available_providers': ['CPUExecutionProvider']}},
        )
        self.assertGreaterEqual(len(failures), 4)
        self.assertTrue(any('outcome=failure' in item for item in failures))
        self.assertTrue(any('missing qualified provider' in item for item in failures))
        self.assertTrue(any('did not execute graph nodes' in item for item in failures))


if __name__ == '__main__':
    unittest.main()
