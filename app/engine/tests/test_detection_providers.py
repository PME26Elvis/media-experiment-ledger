from __future__ import annotations

import unittest

from mel_engine.detection import select_providers


class DetectionProviderSelectionTests(unittest.TestCase):
    def test_selects_requested_provider_without_fallback_in_strict_mode(self) -> None:
        providers, fallback = select_providers(
            'directml',
            ['DmlExecutionProvider', 'CPUExecutionProvider'],
        )
        self.assertEqual(providers, ['DmlExecutionProvider'])
        self.assertFalse(fallback)

    def test_orders_cpu_after_available_accelerator_when_fallback_is_allowed(self) -> None:
        providers, fallback = select_providers(
            'cuda',
            ['CUDAExecutionProvider', 'CPUExecutionProvider'],
            allow_cpu_fallback=True,
        )
        self.assertEqual(providers, ['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.assertFalse(fallback)

    def test_reports_cpu_fallback_when_accelerator_is_unavailable(self) -> None:
        providers, fallback = select_providers(
            'cuda',
            ['CPUExecutionProvider'],
            allow_cpu_fallback=True,
        )
        self.assertEqual(providers, ['CPUExecutionProvider'])
        self.assertTrue(fallback)

    def test_strict_mode_rejects_unavailable_accelerator(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'explicitly enable CPU fallback'):
            select_providers('cuda', ['CPUExecutionProvider'])

    def test_cpu_never_claims_a_fallback(self) -> None:
        providers, fallback = select_providers('cpu', ['CPUExecutionProvider'])
        self.assertEqual(providers, ['CPUExecutionProvider'])
        self.assertFalse(fallback)

    def test_rejects_runtime_without_requested_or_cpu_provider(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'Requested provider'):
            select_providers(
                'coreml',
                ['SomeOtherExecutionProvider'],
                allow_cpu_fallback=True,
            )

    def test_rejects_unknown_provider_key(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsupported execution provider'):
            select_providers('mystery', ['CPUExecutionProvider'])


if __name__ == '__main__':
    unittest.main()
