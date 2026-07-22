import tempfile
import unittest
from pathlib import Path

from PIL import Image

from mel_engine.scan import PROXY_EDGES, run_scan


class ImportPipelineTests(unittest.TestCase):
    def test_managed_copy_creates_content_addressed_media_and_proxy_pyramid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            project = root / 'project'
            source.mkdir()
            Image.new('RGB', (960, 540), 'navy').save(source / 'one.png')
            Image.new('RGB', (960, 540), 'navy').save(source / 'duplicate.png')

            result = run_scan({
                'image_path': str(source),
                'output_path': str(project),
                'import_mode': 'copy',
                'workers': 2,
            })
            self.assertEqual(result['indexed_count'], 2)
            self.assertEqual(result['unique_content_count'], 1)
            self.assertEqual(result['duplicate_content_count'], 1)
            self.assertTrue((project / 'portable-project.json').is_file())
            for record in result['assets']:
                self.assertEqual(record['storage_mode'], 'copy')
                self.assertTrue(Path(record['stored_path']).is_file())
                self.assertEqual([proxy['edge'] for proxy in record['proxies']], list(PROXY_EDGES))
                self.assertTrue(all(Path(proxy['path']).is_file() for proxy in record['proxies']))

    def test_unchanged_import_reuses_verified_index_and_proxies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            project = root / 'project'
            source.mkdir()
            Image.new('RGB', (128, 96), 'teal').save(source / 'one.png')
            first = run_scan({'image_path': str(source), 'output_path': str(project), 'import_mode': 'reference'})
            second = run_scan({'image_path': str(source), 'output_path': str(project), 'import_mode': 'reference'})
            self.assertFalse(first['assets'][0]['reused'])
            self.assertTrue(second['assets'][0]['reused'])
            self.assertEqual(first['assets'][0]['sha256'], second['assets'][0]['sha256'])

    def test_adaptive_import_uses_reference_when_copy_threshold_is_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            project = root / 'project'
            source.mkdir()
            Image.new('RGB', (64, 64), 'red').save(source / 'one.png')
            result = run_scan({
                'image_path': str(source),
                'output_path': str(project),
                'import_mode': 'adaptive',
                'copy_threshold_bytes': 0,
            })
            self.assertEqual(result['effective_storage_mode'], 'reference')


if __name__ == '__main__':
    unittest.main()
