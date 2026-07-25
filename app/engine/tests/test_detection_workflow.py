from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import imageio.v3 as iio
import imageio_ffmpeg
import numpy as np
from PIL import Image

from mel_engine.detection import _encode_annotated_video, _percentile, _write_exports, should_sample_frame


class DetectionWorkflowTests(unittest.TestCase):
    def test_frame_sampling_combines_stride_and_target_fps_deterministically(self) -> None:
        sampled = [
            index
            for index in range(30)
            if should_sample_frame(index, source_fps=30.0, every_n_frames=2, target_fps=5.0)
        ]
        self.assertEqual(sampled, [0, 6, 12, 18, 24])
        self.assertTrue(should_sample_frame(0, source_fps=0.0, every_n_frames=3))
        self.assertFalse(should_sample_frame(-1, source_fps=30.0, every_n_frames=1))

    def test_percentile_is_stable_for_benchmark_evidence(self) -> None:
        self.assertEqual(_percentile([], 95), 0.0)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 50), 2.5)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 95), 3.85)

    def test_annotated_video_rebuilds_all_frames_and_replaces_sampled_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            output = root / 'annotated.mp4'
            writer = imageio_ffmpeg.write_frames(
                str(source),
                (32, 32),
                fps=6,
                codec='libx264',
                pix_fmt_in='rgb24',
                pix_fmt_out='yuv420p',
                ffmpeg_log_level='error',
            )
            writer.send(None)
            try:
                for value in (20, 40, 60):
                    writer.send(np.full((32, 32, 3), value, dtype=np.uint8).tobytes())
            finally:
                writer.close()
            annotation = root / 'frame-1.jpg'
            Image.new('RGB', (32, 32), (240, 10, 10)).save(annotation, 'JPEG', quality=95)

            evidence = _encode_annotated_video(source, output, {1: annotation}, fps=6.0)
            frames = [np.asarray(frame, dtype=np.uint8) for frame in iio.imiter(output)]

            self.assertTrue(output.is_file())
            self.assertEqual(evidence['frame_count'], 3)
            self.assertEqual(evidence['annotation_policy'], 'sampled-frames-only')
            self.assertEqual(len(frames), 3)
            self.assertLess(float(frames[0].mean()), 35.0)
            self.assertGreater(float(frames[1][..., 0].mean()), 180.0)
            self.assertLess(float(frames[1][..., 1].mean()), 60.0)
            self.assertGreater(float(frames[2].mean()), 45.0)

    def test_structured_exports_include_empty_items_crops_and_coco_categories(self) -> None:
        items = [
            {
                'item_id': 'image-1',
                'source_path': '/corpus/image.jpg',
                'source_type': 'image',
                'source_width': 100,
                'source_height': 80,
                'frame_index': None,
                'timestamp_seconds': None,
                'annotated': {'path': '/output/annotated/image-1.jpg'},
                'detections': [
                    {
                        'class_id': 0,
                        'class_name': 'person',
                        'confidence': 0.9,
                        'bbox_xyxy': [10.0, 12.0, 30.0, 42.0],
                        'area_pixels': 600.0,
                        'area_fraction': 0.075,
                        'crop_path': '/output/crops/person/image-1-0000.jpg',
                    },
                ],
            },
            {
                'item_id': 'frame-2',
                'source_path': '/corpus/video.mp4',
                'source_type': 'video-frame',
                'source_width': 1920,
                'source_height': 1080,
                'frame_index': 60,
                'timestamp_seconds': 2.0,
                'annotated': {'path': '/output/cache/frame-2.jpg'},
                'detections': [],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            exports = _write_exports(Path(directory), items, ['person', 'car'])
            for key in ('jsonl', 'csv', 'coco_json', 'class_summary'):
                self.assertTrue(Path(exports[key]).is_file())
            jsonl_rows = Path(exports['jsonl']).read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(jsonl_rows), 2)
            self.assertEqual(json.loads(jsonl_rows[0])['item_id'], 'image-1')
            coco = json.loads(Path(exports['coco_json']).read_text(encoding='utf-8'))
            self.assertEqual(len(coco['images']), 2)
            self.assertEqual(coco['annotations'][0]['bbox'], [10.0, 12.0, 20.0, 30.0])
            self.assertEqual(coco['annotations'][0]['crop_path'], '/output/crops/person/image-1-0000.jpg')
            self.assertEqual(coco['categories'][0], {'id': 1, 'name': 'person'})
            summary = json.loads(Path(exports['class_summary']).read_text(encoding='utf-8'))
            self.assertEqual(summary['boxes'], 1)
            self.assertEqual(summary['classes'], [{'name': 'person', 'count': 1}])
            self.assertEqual(len(exports['annotated_media']), 2)


if __name__ == '__main__':
    unittest.main()
