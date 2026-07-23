from __future__ import annotations

import unittest

from mel_engine.detection import select_providers


class DetectionProviderSelectionTests(unittest.TestCase):
    def test_selects_requested_provider_without_fallback(self) -> None:
        providers, fallback = select_providers(
            'directml',
            ['DmlExecutionProvider', 'CPUExecutionProvider'],
        )
        self.assertEqual(providers, ['DmlExecutionProvider'])
        self.assertFalse(fallback)

    def test_reports_cpu_fallback_when_accelerator_is_unavailable(self) -> None:
        providers, fallback = select_providers('cuda', ['CPUExecutionProvider'])
        self.assertEqual(providers, ['CPUExecutionProvider'])
        self.assertTrue(fallback)

    def test_cpu_never_claims_a_fallback(self) -> None:
        providers, fallback = select_providers('cpu', ['CPUExecutionProvider'])
        self.assertEqual(providers, ['CPUExecutionProvider'])
        self.assertFalse(fallback)

    def test_rejects_runtime_without_requested_or_cpu_provider(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'Neither requested provider'):
            select_providers('coreml', ['SomeOtherExecutionProvider'])


if __name__ == '__main__':
    unittest.main()
