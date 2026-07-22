import json
import tempfile
import unittest
from pathlib import Path
from mel_engine.__main__ import iter_media, run_scan

class EngineTests(unittest.TestCase):
    def test_iter_media_filters_and_sorts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'b.png').write_bytes(b'b'); (root/'a.jpg').write_bytes(b'a'); (root/'ignore.txt').write_text('x')
            self.assertEqual([p.name for p in iter_media([directory])], ['a.jpg','b.png'])

    def test_scan_writes_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'sample.jpg').write_bytes(b'content')
            result=run_scan({'image_path':directory})
            self.assertEqual(result['count'],1)
            self.assertEqual(len(result['assets'][0]['sha256']),64)

if __name__ == '__main__': unittest.main()
