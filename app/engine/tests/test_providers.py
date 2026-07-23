from __future__ import annotations

import unittest
from unittest import mock

from mel_engine.providers import PROVIDER_MAP, provider_inventory


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

        self.assertEqual(inventory['schema_version'], 1)
        self.assertEqual(inventory['runtime_version'], '1.99.0')
        self.assertTrue(inventory['provider_support']['cpu']['available'])
        self.assertTrue(inventory['provider_support']['directml']['available'])
        self.assertFalse(inventory['provider_support']['cuda']['available'])
        self.assertFalse(inventory['provider_support']['coreml']['available'])
        self.assertEqual(inventory['distributions'], {'onnxruntime-directml': '1.99.0'})


if __name__ == '__main__':
    unittest.main()
