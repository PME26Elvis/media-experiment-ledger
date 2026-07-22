from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
VIDEO_SUFFIXES = {'.gif', '.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi'}
MAX_PART_BYTES = 1_900_000_000
ZIP_OVERHEAD_RESERVE = 16 * 1024 * 1024


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name.replace('\\', '/'))
    if member.is_absolute() or '..' in member.parts or not member.name:
        raise ValueError(f'Unsafe archive member: {name}')
    return member


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size=size)
    except OSError:
        return ImageFont.load_default()


def color(index: int, offset: int = 0) -> tuple[int, int, int]:
    randomizer = random.Random(index * 104729 + offset * 15485863)
    return tuple(randomizer.randint(28, 232) for _ in range(3))


def procedural_image(index: int, destination: Path) -> dict[str, Any]:
    width = 768 + (index % 4) * 128
    height = 512 + (index % 3) * 128
    background = color(index, 1)
    image = Image.new('RGB', (width, height), background)
    draw = ImageDraw.Draw(image, 'RGBA')
    rng = random.Random(index)
    for shape_index in range(18 + index % 12):
        x1 = rng.randint(-80, width - 40)
        y1 = rng.randint(-80, height - 40)
        x2 = x1 + rng.randint(50, max(80, width // 2))
        y2 = y1 + rng.randint(50, max(80, height // 2))
        fill = (*color(index, shape_index + 2), rng.randint(80, 210))
        if shape_index % 3 == 0:
            draw.ellipse((x1, y1, x2, y2), fill=fill)
        elif shape_index % 3 == 1:
            draw.rounded_rectangle((x1, y1, x2, y2), radius=rng.randint(8, 48), fill=fill)
        else:
            draw.polygon(((x1, y2), ((x1 + x2) // 2, y1), (x2, y2)), fill=fill)
    label = f'MEL Studio Quick Start · image {index:03d}'
    draw.rounded_rectangle((24, height - 76, width - 24, height - 20), radius=16, fill=(4, 10, 24, 190))
    draw.text((42, height - 62), label, fill=(245, 248, 255, 255), font=font(24))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format='PNG', optimize=True)
    return {
        'path': destination,
        'mediaType': 'image',
        'width': width,
        'height': height,
        'frames': 1,
        'source': 'procedural-mel-studio-v1',
    }


def procedural_gif(index: int, destination: Path) -> dict[str, Any]:
    width, height = 640, 360
    frames: list[Image.Image] = []
    frame_count = 24
    for frame_index in range(frame_count):
        image = Image.new('RGB', (width, height), color(index, frame_index + 100))
        draw = ImageDraw.Draw(image, 'RGBA')
        phase = frame_index / frame_count * math.tau
        for orbit in range(7):
            radius = 34 + orbit * 18
            center_x = width / 2 + math.cos(phase + orbit * 0.7) * (80 + orbit * 12)
            center_y = height / 2 + math.sin(phase * 1.3 + orbit * 0.5) * (45 + orbit * 8)
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                fill=(*color(index, orbit + 200), 170),
            )
        draw.text((20, 18), f'MEL motion sample {index:02d} · {frame_index + 1:02d}/{frame_count}', fill='white', font=font(20))
        frames.append(image)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        destination,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return {
        'path': destination,
        'mediaType': 'video',
        'width': width,
        'height': height,
        'frames': frame_count,
        'durationSeconds': frame_count * 0.09,
        'source': 'procedural-mel-studio-v1',
    }


def build_procedural_quick_start(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(1, 65):
        records.append(procedural_image(index, root / 'media' / 'images' / f'image-{index:03d}.png'))
    for index in range(1, 9):
        records.append(procedural_gif(index, root / 'media' / 'videos' / f'motion-{index:02d}.gif'))
    return records


def load_rights(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or int(value.get('schema_version') or 0) != 1:
        raise ValueError('Rights attestation must be a schema_version=1 JSON object.')
    return value


def validate_rights(rights: dict[str, Any], source_tags: list[str]) -> None:
    if rights.get('status') != 'approved':
        raise ValueError('Full Research corpus publication requires status=approved in the rights attestation.')
    approved_tags = {str(tag) for tag in rights.get('source_release_tags') or []}
    missing = sorted(set(source_tags).difference(approved_tags))
    if missing:
        raise ValueError(f'Rights attestation does not approve source releases: {", ".join(missing)}')
    if not str(rights.get('license') or '').strip():
        raise ValueError('Rights attestation must state the corpus distribution license.')
    if not str(rights.get('approved_by') or '').strip() or not str(rights.get('approved_at') or '').strip():
        raise ValueError('Rights attestation requires approved_by and approved_at evidence.')
    if not bool(rights.get('model_output_redistribution_reviewed')):
        raise ValueError('Rights attestation must confirm model output redistribution review.')
    if not bool(rights.get('privacy_reviewed')):
        raise ValueError('Rights attestation must confirm privacy review.')


def extract_archives(download_root: Path, extract_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for archive in sorted(download_root.rglob('*.zip')):
        with zipfile.ZipFile(archive) as bundle:
            for info in sorted(bundle.infolist(), key=lambda item: item.filename):
                if info.is_dir():
                    continue
                member = safe_member(info.filename)
                suffix = member.suffix.lower()
                if suffix not in IMAGE_SUFFIXES | VIDEO_SUFFIXES:
                    continue
                if info.file_size > MAX_PART_BYTES:
                    raise ValueError(f'Individual source media exceeds corpus part limit: {archive}:{member}')
                with bundle.open(info) as stream:
                    content = stream.read()
                digest = hashlib.sha256(content).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                media_type = 'image' if suffix in IMAGE_SUFFIXES else 'video'
                destination = extract_root / 'media' / ('images' if media_type == 'image' else 'videos') / f'{digest[:20]}{suffix}'
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                records.append({
                    'path': destination,
                    'mediaType': media_type,
                    'source': 'release-archive',
                    'sourceArchive': archive.name,
                    'sourceMember': member.as_posix(),
                })
    if not records:
        raise ValueError(f'No supported media found below {download_root}')
    return records


def sanitized_inventory(records: list[dict[str, Any]], root: Path, prompts: str) -> dict[str, Any]:
    assets = []
    for record in sorted(records, key=lambda item: str(item['path'])):
        path = Path(record['path'])
        row = {
            'path': path.relative_to(root).as_posix(),
            'media_type': record['mediaType'],
            'size_bytes': path.stat().st_size,
            'sha256': sha256_file(path),
            'source': record.get('source'),
        }
        for key in ('width', 'height', 'frames', 'durationSeconds'):
            if key in record:
                row[key] = record[key]
        if prompts == 'ids-only':
            row['prompt_id'] = f"sample-{row['sha256'][:16]}"
        assets.append(row)
    return {
        'schema_version': 1,
        'scope': 'studio-sample-corpus',
        'asset_count': len(assets),
        'image_count': sum(1 for item in assets if item['media_type'] == 'image'),
        'video_count': sum(1 for item in assets if item['media_type'] == 'video'),
        'total_bytes': sum(int(item['size_bytes']) for item in assets),
        'assets': assets,
    }


def partition(paths: Iterable[Path], maximum: int) -> list[list[Path]]:
    groups: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    for path in sorted(paths, key=lambda item: item.as_posix()):
        size = path.stat().st_size
        if size + ZIP_OVERHEAD_RESERVE > maximum:
            raise ValueError(f'File cannot fit below part size limit: {path}')
        if current and current_size + size + ZIP_OVERHEAD_RESERVE > maximum:
            groups.append(current)
            current = []
            current_size = 0
        current.append(path)
        current_size += size
    if current:
        groups.append(current)
    return groups


def write_zip(paths: list[Path], root: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as bundle:
        for path in paths:
            member = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(member, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, path.read_bytes())
    if temporary.stat().st_size > MAX_PART_BYTES:
        temporary.unlink(missing_ok=True)
        raise ValueError(f'ZIP part exceeds {MAX_PART_BYTES} bytes: {destination}')
    temporary.replace(destination)


def release_url(tag: str, file_name: str) -> str:
    return f'https://github.com/PME26Elvis/media-experiment-ledger/releases/download/{quote(tag, safe="")}/{quote(file_name, safe="")}'


def build(args: argparse.Namespace) -> Path:
    tier = args.tier
    version = int(args.version)
    tag = args.release_tag or f'studio-sample-corpus-{tier}-v{version}'
    output = Path(args.output).resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='mel-sample-corpus-') as directory:
        working = Path(directory) / 'corpus'
        working.mkdir(parents=True)
        if tier == 'quick-start':
            records = build_procedural_quick_start(working)
            source_tags: list[str] = []
            rights_status = 'approved'
            license_name = 'CC0-1.0'
            prompt_policy = 'ids-only'
            removed_fields = ['provider_account', 'api_key', 'remote_task_id', 'raw_headers', 'user_identity']
            rights_evidence = {
                'schema_version': 1,
                'status': 'approved',
                'basis': 'Deterministic procedural assets authored by this repository; no third-party media or model output.',
                'license': license_name,
            }
        else:
            source_tags = [tag.strip() for tag in args.source_release_tags.split(',') if tag.strip()]
            if not source_tags:
                raise ValueError('Full Research corpus requires --source-release-tags.')
            if not args.rights_attestation:
                raise ValueError('Full Research corpus requires --rights-attestation.')
            rights = load_rights(Path(args.rights_attestation))
            validate_rights(rights, source_tags)
            records = extract_archives(Path(args.download_root).resolve(), working)
            rights_status = 'approved'
            license_name = str(rights['license'])
            prompt_policy = str(rights.get('prompt_policy') or 'ids-only')
            if prompt_policy not in {'ids-only', 'sanitized-full'}:
                raise ValueError('prompt_policy must be ids-only or sanitized-full.')
            removed_fields = [str(item) for item in rights.get('removed_fields') or []]
            rights_evidence = {
                'schema_version': 1,
                'status': 'approved',
                'approved_by': rights['approved_by'],
                'approved_at': rights['approved_at'],
                'license': license_name,
                'source_release_tags': source_tags,
                'model_output_redistribution_reviewed': True,
                'privacy_reviewed': True,
                'attestation_sha256': sha256_file(Path(args.rights_attestation)),
            }

        inventory = sanitized_inventory(records, working, prompt_policy)
        atomic_json(working / 'metadata' / 'inventory.json', inventory)
        atomic_json(working / 'metadata' / 'rights-evidence.json', rights_evidence)
        atomic_json(working / 'metadata' / 'corpus-identity.json', {
            'schema_version': 1,
            'tier': tier,
            'version': version,
            'release_tag': tag,
            'inventory_fingerprint': hashlib.sha256(canonical_json(inventory).encode()).hexdigest(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        })

        media_paths = [path for path in working.rglob('*') if path.is_file()]
        groups = partition(media_paths, MAX_PART_BYTES)
        manifest_assets: list[dict[str, Any]] = []
        for part, paths in enumerate(groups, 1):
            file_name = f'mel-sample-corpus-{tier}-v{version}-part{part:03d}.zip'
            destination = output / file_name
            write_zip(paths, working, destination)
            media_types = {
                'image' if path.suffix.lower() in IMAGE_SUFFIXES else
                'video' if path.suffix.lower() in VIDEO_SUFFIXES else
                'metadata'
                for path in paths
            }
            manifest_assets.append({
                'id': f'{tier}-v{version}-part-{part:03d}',
                'mediaType': next(iter(media_types)) if len(media_types) == 1 else 'mixed',
                'part': part,
                'fileName': file_name,
                'url': release_url(tag, file_name),
                'sha256': sha256_file(destination),
                'sizeBytes': destination.stat().st_size,
                'required': True,
            })

    manifest = {
        'schemaVersion': 1,
        'id': f'mel-{tier}',
        'tier': tier,
        'version': version,
        'title': 'MEL Studio Quick Start Corpus' if tier == 'quick-start' else 'MEL Studio Full Research Corpus',
        'description': 'Deterministic procedural images and motion samples for local workflow validation.' if tier == 'quick-start' else 'Rights-reviewed, sanitized research corpus derived from immutable project releases.',
        'releaseTag': tag,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'rightsStatus': rights_status,
        'license': license_name,
        'sourceReleaseTags': source_tags,
        'sanitization': {
            'prompts': prompt_policy,
            'removedFields': removed_fields,
        },
        'assets': manifest_assets,
    }
    atomic_json(output / 'corpus-manifest.json', manifest)
    atomic_json(output / 'build-evidence.json', {
        'schema_version': 1,
        'manifest_sha256': sha256_file(output / 'corpus-manifest.json'),
        'release_tag': tag,
        'part_count': len(manifest_assets),
        'total_bytes': sum(item['sizeBytes'] for item in manifest_assets),
        'max_part_bytes': max((item['sizeBytes'] for item in manifest_assets), default=0),
        'rights_status': rights_status,
        'source_release_tags': source_tags,
    })
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tier', choices=('quick-start', 'full-research'), required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--release-tag')
    parser.add_argument('--output', required=True)
    parser.add_argument('--download-root', default='sample-corpus-inputs')
    parser.add_argument('--source-release-tags', default='')
    parser.add_argument('--rights-attestation')
    return parser.parse_args()


if __name__ == '__main__':
    output = build(parse_args())
    print(json.dumps({'output': str(output)}, indent=2))
