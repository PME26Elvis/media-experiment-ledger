from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mel_engine import detection
from mel_engine.__main__ import process_line


class FakeSession:
    def get_inputs(self):
        return [SimpleNamespace(name='input')]

    def get_outputs(self):
        return [SimpleNamespace(name='output')]


class PersistentEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        detection._SESSION_CACHE.clear()

    def test_process_line_can_dispatch_multiple_independent_requests(self) -> None:
        events: list[tuple[str, dict]] = []
        with mock.patch('mel_engine.__main__.dispatch', side_effect=[{'sequence': 1}, {'sequence': 2}]), mock.patch(
            'mel_engine.__main__.emit',
            side_effect=lambda event_type, **payload: events.append((event_type, payload)),
        ):
            self.assertTrue(process_line('{"operation":"providers"}'))
            self.assertTrue(process_line('{"operation":"providers"}'))
        results = [payload['data']['sequence'] for event_type, payload in events if event_type == 'result']
        self.assertEqual(results, [1, 2])

    def test_process_line_reports_an_error_without_poisoning_the_protocol(self) -> None:
        events: list[tuple[str, dict]] = []
        with mock.patch('mel_engine.__main__.dispatch', side_effect=ValueError('bad request')), mock.patch(
            'mel_engine.__main__.emit',
            side_effect=lambda event_type, **payload: events.append((event_type, payload)),
        ):
            self.assertFalse(process_line('{"operation":"bad"}'))
        self.assertEqual(events[-1][0], 'error')
        self.assertIn('ValueError', events[-1][1]['message'])

    def test_detection_session_is_reused_for_the_same_model_provider_and_device(self) -> None:
        created: list[FakeSession] = []

        def create_session(*_args, **_kwargs):
            session = FakeSession()
            created.append(session)
            return session

        fake_ort = SimpleNamespace(InferenceSession=create_session, get_available_providers=lambda: ['CPUExecutionProvider'])
        plan = {
            'active_provider': 'CPUExecutionProvider',
            'providers': ['CPUExecutionProvider'],
            'provider_names': ['CPUExecutionProvider'],
            'provider_options': [{}],
            'provider_fallback': False,
        }
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'model.onnx'
            model.write_bytes(b'model')
            with mock.patch('mel_engine.detection.prepare_runtime'), mock.patch(
                'mel_engine.detection.provider_plan', return_value=plan,
            ), mock.patch('mel_engine.detection.create_session_options', return_value=object()):
                first = detection._session_for(fake_ort, model, 'abc', 'cpu', True, 0, 'ALL')
                second = detection._session_for(fake_ort, model, 'abc', 'cpu', True, 0, 'ALL')
        self.assertFalse(first[-1])
        self.assertTrue(second[-1])
        self.assertEqual(len(created), 1)
        self.assertIs(first[0], second[0])


if __name__ == '__main__':
    unittest.main()
