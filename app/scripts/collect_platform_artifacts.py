from __future__ import annotations

import argparse
import shutil
from pathlib import Path

IGNORED_SUFFIXES = {'.blockmap'}
IGNORED_NAMES = {
    'builder-debug.yml',
    'builder-effective-config.yaml',
}
PACKAGE_SUFFIXES = {'.exe', '.dmg', '.zip', '.appimage', '.deb'}
METADATA_SUFFIXES = {'.yml', '.yaml', '.json'}


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform-id', required=True)
    args = parser.parse_args()
    app_root = Path(__file__).resolve().parents[1]
    output = app_root / 'artifact-out'
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)

    release_root = app_root / 'release'
    copied = 0
    for path in sorted(release_root.rglob('*')):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if path.name in IGNORED_NAMES or suffix in IGNORED_SUFFIXES:
            continue
        if suffix not in PACKAGE_SUFFIXES | METADATA_SUFFIXES:
            continue
        destination_name = (
            path.name
            if suffix in PACKAGE_SUFFIXES
            else f'{args.platform_id}-{path.name}'
        )
        destination = output / destination_name
        if destination.exists():
            raise RuntimeError(
                f'Duplicate collected release asset name for {args.platform_id}: '
                f'{destination_name}'
            )
        copy(path, destination)
        copied += 1

    evidence_root = app_root / 'release-evidence'
    for path in sorted(evidence_root.glob('*')):
        if path.is_file():
            destination = output / f'{args.platform_id}-{path.name}'
            if destination.exists():
                raise RuntimeError(f'Duplicate release evidence name: {destination.name}')
            copy(path, destination)
            copied += 1

    evidence = app_root / 'packaged-smoke-evidence.json'
    if evidence.is_file():
        copy(
            evidence,
            output / f'{args.platform_id}-packaged-smoke-evidence.json',
        )
        copied += 1

    engine_manifest = app_root / 'engine-bin' / 'mel-engine' / 'engine-build-manifest.json'
    if not engine_manifest.is_file():
        raise RuntimeError('Self-contained engine build manifest is missing.')
    copy(engine_manifest, output / f'{args.platform_id}-engine-build-manifest.json')
    copied += 1

    if copied == 0:
        raise RuntimeError('No platform artifacts were collected.')
    print(f'Collected {copied} files for {args.platform_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
