import tempfile
import unittest
from pathlib import Path

from mel_engine.common import iter_media
from mel_engine.detection import select_providers
from mel_engine.scan import run_scan


class EngineTests(unittest.TestCase):
    def test_iter_media_filters_and_sorts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'b.png').write_bytes(b'b')
            (root / 'a.jpg').write_bytes(b'a')
            (root / 'ignore.txt').write_text('x')
            self.assertEqual([path.name for path in iter_media([directory])], ['a.jpg', 'b.png'])

    def test_scan_writes_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sample.jpg').write_bytes(b'content')
            result = run_scan({'image_path': directory})
            self.assertEqual(result['count'], 1)
            self.assertEqual(len(result['assets'][0]['sha256']), 64)

    def test_execution_provider_falls_back_to_cpu(self):
        providers, fallback = select_providers('cuda', ['CPUExecutionProvider'])
        self.assertEqual(providers, ['CPUExecutionProvider'])
        self.assertTrue(fallback)

    def test_execution_provider_keeps_available_acceleration(self):
        providers, fallback = select_providers('coreml', ['CoreMLExecutionProvider', 'CPUExecutionProvider'])
        self.assertEqual(providers, ['CoreMLExecutionProvider'])
        self.assertFalse(fallback)


if __name__ == '__main__':
    unittest.main()
