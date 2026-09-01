from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from mel_engine.hardware import hardware_diagnostics, run_provider_self_test, tiny_identity_model


class HardwareRuntimeTests(unittest.TestCase):
    def test_generated_identity_graph_loads_and_executes_in_cpu_runtime(self) -> None:
        import onnxruntime as ort

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'identity.onnx'
            path.write_bytes(tiny_identity_model())
            session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            tensor = np.asarray([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
            output = np.asarray(session.run([output_name], {input_name: tensor})[0])
        self.assertTrue(np.array_equal(output, tensor))

    def test_cpu_self_test_proves_registration_session_and_node_assignment(self) -> None:
        result = run_provider_self_test({
            'provider': 'cpu',
            'device_id': 0,
            'allow_cpu_fallback': True,
            'coreml_compute_units': 'ALL',
            'warm_runs': 2,
        })
        self.assertTrue(result['registered'])
        self.assertTrue(result['session_created'])
        self.assertGreater(result['cpu_assigned_node_count'], 0)
        self.assertTrue(result['passed'])
        self.assertEqual(result['status'], 'passed')

    def test_hardware_diagnostics_extends_provider_inventory_with_host_resources(self) -> None:
        result = hardware_diagnostics()
        self.assertGreaterEqual(result['cpu']['logical_cores'], 1)
        self.assertIn('total_bytes', result['host_memory'])
        self.assertIn('available_bytes', result['host_memory'])


if __name__ == '__main__':
    unittest.main()
