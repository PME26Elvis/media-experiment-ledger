from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

from mel_engine.scan import run_scan


def memory_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.name == 'posix' and os.uname().sysname == 'Darwin':
        return value / 1024 / 1024
    return value / 1024


def build_images(root: Path, count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        path = root / f'image-{index:05d}.jpg'
        image = Image.new('RGB', (96, 64), ((index * 31) % 255, (index * 67) % 255, (index * 97) % 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((index % 48, index % 32, 95 - index % 48, 63 - index % 32), outline='white', width=2)
        image.save(path, format='JPEG', quality=70, optimize=True)


def build_gifs(root: Path, count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        frames = [
            Image.new('RGB', (64, 40), ((index * 17 + frame * 51) % 255, (index * 29 + frame * 73) % 255, (index * 43 + frame * 89) % 255))
            for frame in range(3)
        ]
        frames[0].save(root / f'video-{index:04d}.gif', save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=True)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[position]


def sample_proxy_latency(manifest: dict, sample_count: int = 200) -> dict[str, float]:
    timings = []
    assets = manifest.get('assets', [])[:sample_count]
    for asset in assets:
        proxies = asset.get('proxies') or []
        if not proxies:
            continue
        path = Path(proxies[min(1, len(proxies) - 1)]['path'])
        started = time.perf_counter()
        with Image.open(path) as image:
            image.load()
        timings.append((time.perf_counter() - started) * 1000)
    return {
        'samples': len(timings),
        'mean_ms': round(statistics.fmean(timings), 4) if timings else 0.0,
        'p50_ms': round(percentile(timings, 0.50), 4),
        'p95_ms': round(percentile(timings, 0.95), 4),
        'max_ms': round(max(timings), 4) if timings else 0.0,
    }


def run(args: argparse.Namespace) -> dict:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mel-large-corpus-') as directory:
        root = Path(directory)
        images = root / 'images'
        videos = root / 'videos'
        generated_started = time.perf_counter()
        build_images(images, args.images)
        build_gifs(videos, args.videos)
        generated_seconds = time.perf_counter() - generated_started

        memory_before = memory_mib()
        first_started = time.perf_counter()
        first = run_scan({
            'image_path': str(images),
            'video_path': str(videos),
            'output_path': str(output / 'project'),
            'import_mode': 'reference',
            'workers': args.workers,
        })
        first_seconds = time.perf_counter() - first_started
        memory_after_first = memory_mib()
        latency = sample_proxy_latency(first)

        resume_started = time.perf_counter()
        resumed = run_scan({
            'image_path': str(images),
            'video_path': str(videos),
            'output_path': str(output / 'project'),
            'import_mode': 'reference',
            'workers': args.workers,
        })
        resume_seconds = time.perf_counter() - resume_started
        memory_after_resume = memory_mib()

    expected = args.images + args.videos
    reused = sum(1 for asset in resumed.get('assets', []) if asset.get('reused'))
    report = {
        'schema_version': 1,
        'scenario': {'images': args.images, 'videos': args.videos, 'workers': args.workers},
        'generation_seconds': round(generated_seconds, 3),
        'first_index_seconds': round(first_seconds, 3),
        'first_assets_per_second': round(expected / first_seconds, 3) if first_seconds else None,
        'resume_seconds': round(resume_seconds, 3),
        'resume_assets_per_second': round(expected / resume_seconds, 3) if resume_seconds else None,
        'indexed_count': first.get('indexed_count'),
        'error_count': first.get('error_count'),
        'resume_reused_count': reused,
        'proxy_open_latency': latency,
        'peak_memory_mib': {
            'before': round(memory_before, 3),
            'after_first': round(memory_after_first, 3),
            'after_resume': round(memory_after_resume, 3),
        },
        'acceptance': {
            'all_assets_indexed': first.get('indexed_count') == expected,
            'no_errors': first.get('error_count') == 0,
            'full_resume_reuse': reused == expected,
            'p95_proxy_open_under_100ms': latency['p95_ms'] < 100,
            'peak_memory_under_2048mib': max(memory_before, memory_after_first, memory_after_resume) < 2048,
        },
    }
    report['passed'] = all(report['acceptance'].values())
    path = output / 'large-corpus-benchmark.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit('Large-corpus acceptance thresholds failed.')
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', type=int, default=10_000)
    parser.add_argument('--videos', type=int, default=1_000)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--output', default='performance-evidence')
    return parser.parse_args()


if __name__ == '__main__':
    run(parse_args())
