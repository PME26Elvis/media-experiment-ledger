from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mel_engine.providers import (
    PROVIDER_MAP,
    create_session_options,
    provider_inventory,
    provider_options,
    provider_plan,
)


class FakeSessionOptions:
    def __init__(self) -> None:
        self.graph_optimization_level = None
        self.enable_profiling = False
        self.profile_file_prefix = ''
        self.enable_mem_pattern = True
        self.execution_mode = None
        self.config_entries: dict[str, str] = {}

    def add_session_config_entry(self, key: str, value: str) -> None:
        self.config_entries[key] = value


class ProviderInventoryTests(unittest.TestCase):
    def test_provider_names_match_detection_selection_contract(self) -> None:
        self.assertEqual(PROVIDER_MAP['cpu'], 'CPUExecutionProvider')
        self.assertEqual(PROVIDER_MAP['cuda'], 'CUDAExecutionProvider')
        self.assertEqual(PROVIDER_MAP['directml'], 'DmlExecutionProvider')
        self.assertEqual(PROVIDER_MAP['coreml'], 'CoreMLExecutionProvider')

    def test_inventory_reports_canonical_support_without_claiming_unavailable_providers(self) -> None:
        fake_runtime = mock.Mock()
        fake_runtime.__version__ = '1.99.0'
        fake_runtime.get_device.return_value = 'CPU'
        fake_runtime.get_available_providers.return_value = [
            'DmlExecutionProvider',
            'CPUExecutionProvider',
        ]
        with mock.patch.dict('sys.modules', {'onnxruntime': fake_runtime}), mock.patch(
            'mel_engine.providers._distribution_versions',
            return_value={'onnxruntime-directml': '1.99.0'},
        ):
            inventory = provider_inventory()

        self.assertEqual(inventory['schema_version'], 2)
        self.assertEqual(inventory['runtime_version'], '1.99.0')
        self.assertTrue(inventory['provider_support']['cpu']['available'])
        self.assertTrue(inventory['provider_support']['directml']['available'])
        self.assertFalse(inventory['provider_support']['cuda']['available'])
        self.assertFalse(inventory['provider_support']['coreml']['available'])
        self.assertEqual(inventory['distributions'], {'onnxruntime-directml': '1.99.0'})

    def test_coreml_plan_uses_official_options_cache_and_ordered_cpu_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'model.onnx'
            model.write_bytes(b'model')
            plan = provider_plan(
                'coreml',
                ['CoreMLExecutionProvider', 'CPUExecutionProvider'],
                allow_cpu_fallback=True,
                model_path=model,
            )

        self.assertEqual(plan['provider_names'], ['CoreMLExecutionProvider', 'CPUExecutionProvider'])
        options = plan['provider_options'][0]
        self.assertEqual(options['ModelFormat'], 'MLProgram')
        self.assertEqual(options['MLComputeUnits'], 'ALL')
        self.assertEqual(options['RequireStaticInputShapes'], '0')
        self.assertEqual(options['EnableOnSubgraphs'], '0')
        self.assertEqual(Path(options['ModelCacheDirectory']).parts[-2:], ('.mel-provider-cache', 'coreml'))

    def test_cuda_plan_exposes_device_and_safe_copy_options(self) -> None:
        options = provider_options('CUDAExecutionProvider', device_id=2)
        self.assertEqual(options, {
            'device_id': '2',
            'arena_extend_strategy': 'kSameAsRequested',
            'do_copy_in_default_stream': '1',
        })

    def test_directml_session_disables_parallelism_and_memory_patterns(self) -> None:
        fake_runtime = SimpleNamespace(
            SessionOptions=FakeSessionOptions,
            GraphOptimizationLevel=SimpleNamespace(ORT_ENABLE_ALL='all'),
            ExecutionMode=SimpleNamespace(ORT_SEQUENTIAL='sequential'),
        )
        options = create_session_options(
            fake_runtime,
            primary_provider='DmlExecutionProvider',
            allow_cpu_fallback=True,
        )
        self.assertFalse(options.enable_mem_pattern)
        self.assertEqual(options.execution_mode, 'sequential')
        self.assertEqual(options.graph_optimization_level, 'all')

    def test_strict_accelerator_session_disables_implicit_cpu_fallback(self) -> None:
        fake_runtime = SimpleNamespace(
            SessionOptions=FakeSessionOptions,
            GraphOptimizationLevel=SimpleNamespace(ORT_ENABLE_ALL='all'),
            ExecutionMode=SimpleNamespace(ORT_SEQUENTIAL='sequential'),
        )
        options = create_session_options(
            fake_runtime,
            primary_provider='CUDAExecutionProvider',
            allow_cpu_fallback=False,
        )
        self.assertEqual(options.config_entries, {'session.disable_cpu_ep_fallback': '1'})


if __name__ == '__main__':
    unittest.main()
