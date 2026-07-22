import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from mel_engine.atlas import extract_video_evidence, run_atlas
from mel_engine.automation import ApiError, CircuitBreaker, classify_error, load_prompts, parse_retry_after
from mel_engine.common import iter_media, sha256
from mel_engine.detection import select_providers
from mel_engine.generated_collection import finalize_generated_collection, validate_media
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

    def test_prompt_loader_supports_text_and_jsonl_without_persisting_raw_prompt_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prompts.jsonl'
            path.write_text(
                'plain prompt\n'
                '{"id":"hero shot","category":"cinematic","prompt":"JSON prompt"}\n',
                encoding='utf-8',
            )
            prompts = load_prompts(path)
            self.assertEqual([prompt.id for prompt in prompts], ['p00001', 'hero-shot'])
            self.assertEqual(prompts[1].category, 'cinematic')
            self.assertEqual(len(prompts[0].digest), 64)

    def test_prompt_loader_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prompts.jsonl'
            path.write_text(
                '{"id":"same","prompt":"one"}\n{"id":"same","prompt":"two"}\n',
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'Duplicate prompt IDs'):
                load_prompts(path)

    def test_retry_after_supports_seconds_and_http_dates(self):
        now = datetime(2026, 7, 22, tzinfo=timezone.utc)
        self.assertEqual(parse_retry_after('90', now=now), 90)
        future = (now + timedelta(seconds=45)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertEqual(parse_retry_after(future, now=now), 45)
        self.assertIsNone(parse_retry_after('not-a-date', now=now))

    def test_error_classifier_distinguishes_terminal_and_retryable_failures(self):
        auth = classify_error(ApiError(401, 'unauthorized'), {})
        self.assertTrue(auth.terminal)
        self.assertTrue(auth.stop_run)
        rate = classify_error(ApiError(429, 'rate limit', retry_after='30'), {})
        self.assertFalse(rate.terminal)
        self.assertFalse(rate.stop_run)
        self.assertEqual(rate.retry_after_seconds, 30)
        quota = classify_error(ApiError(402, 'quota exhausted'), {'stop_on_quota_or_payment': True})
        self.assertTrue(quota.stop_run)

    def test_circuit_breaker_opens_for_consecutive_and_rolling_failures(self):
        consecutive = CircuitBreaker(2, 10, 0.9, 5)
        consecutive.record(False)
        self.assertIsNone(consecutive.reason())
        consecutive.record(False)
        self.assertIn('consecutive', consecutive.reason() or '')

        rolling = CircuitBreaker(10, 4, 0.5, 4)
        for success in (True, False, False, False):
            rolling.record(success)
        self.assertIn('rolling error rate', rolling.reason() or '')

    def test_gif_video_evidence_contains_three_frame_strip_poster_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'animated.gif'
            frames = [Image.new('RGB', (80, 48), color) for color in ('red', 'green', 'blue', 'white')]
            frames[0].save(source, save_all=True, append_images=frames[1:], duration=100, loop=0)
            evidence = extract_video_evidence(source, root / 'output')
            self.assertEqual(evidence['percentages'], [0.1, 0.5, 0.9])
            self.assertEqual(evidence['frame_count'], 4)
            self.assertTrue(Path(evidence['strip']['path']).is_file())
            self.assertTrue(Path(evidence['poster']['path']).is_file())
            self.assertTrue(Path(evidence['gif_preview']['path']).is_file())
            self.assertEqual(len(evidence['strip']['sha256']), 64)

    def test_atlas_manifest_separates_image_and_video_evidence_and_is_resumable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / 'inputs'
            output = root / 'output'
            inputs.mkdir()
            Image.new('RGB', (64, 64), 'purple').save(inputs / 'image.png')
            frames = [Image.new('RGB', (64, 48), color) for color in ('black', 'gray', 'white')]
            frames[0].save(inputs / 'clip.gif', save_all=True, append_images=frames[1:], duration=120, loop=0)
            first = run_atlas({'input_path': str(inputs), 'output_path': str(output), 'template': 'Research Light'})
            second = run_atlas({'input_path': str(inputs), 'output_path': str(output), 'template': 'Research Light'})
            self.assertEqual(first['fingerprint'], second['fingerprint'])
            self.assertEqual(first['image_source_count'], 1)
            self.assertEqual(first['video_source_count'], 1)
            self.assertEqual(len(first['image_pages']), 1)
            self.assertEqual(len(first['video_pages']), 1)
            self.assertEqual(first['pages'][0]['sha256'], second['pages'][0]['sha256'])

    def test_generated_collection_only_enrolls_verified_successful_media(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / 'media' / 'images'
            media.mkdir(parents=True)
            valid = media / 'valid.png'
            invalid = media / 'invalid.png'
            Image.new('RGB', (48, 32), 'orange').save(valid)
            invalid.write_bytes(b'not-an-image')
            result = finalize_generated_collection(
                {
                    'output_path': str(root),
                    'provider': 'agnes',
                    'model': 'test',
                    'media_type': 'image',
                    'auto_enroll_named_corpus': True,
                    'collection_name': 'Accepted outputs',
                },
                {
                    'fingerprint': 'f' * 64,
                    'completed': {
                        'good': {
                            'prompt_sha256': '1' * 64,
                            'category': 'test',
                            'media_type': 'image',
                            'model': 'test',
                            'local': {'path': str(valid), 'sha256': sha256(valid)},
                        },
                        'bad': {
                            'prompt_sha256': '2' * 64,
                            'category': 'test',
                            'media_type': 'image',
                            'model': 'test',
                            'local': {'path': str(invalid), 'sha256': sha256(invalid)},
                        },
                    },
                },
            )
            collection = result['generated_media_collection']
            self.assertEqual(collection['valid_asset_count'], 1)
            self.assertEqual(collection['quarantined_asset_count'], 1)
            self.assertTrue(Path(collection['manifest_path']).is_file())
            self.assertTrue((root / 'named-corpora' / 'accepted-outputs' / 'manifest.json').is_file())
            self.assertTrue(any((root / 'quarantine').iterdir()))

    def test_generated_media_validation_rejects_corrupt_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.png'
            path.write_bytes(b'bad')
            with self.assertRaises(Exception):
                validate_media(path, 'image')


if __name__ == '__main__':
    unittest.main()
