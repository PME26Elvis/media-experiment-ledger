from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PACKAGE_SUFFIXES = {'.exe', '.dmg', '.zip', '.appimage', '.deb'}
UPDATE_METADATA_NAMES = {'latest.yml', 'latest-mac.yml', 'latest-linux.yml'}
PACKAGE_PREFIX = 'Media-Experiment-Ledger-Studio-'


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def collect_platform_artifacts(app_root: Path, platform_id: str) -> list[str]:
    app_root = app_root.resolve()
    output = app_root / 'artifact-out'
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    release_root = app_root / 'release'
    if not release_root.is_dir():
        raise RuntimeError('electron-builder release directory is missing.')

    # Only publish electron-builder's top-level package outputs. Recursive scans
    # previously captured unpacked executables, bundled Python files and runtime
    # resources as standalone public Release assets.
    for path in sorted(release_root.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if path.name.startswith(PACKAGE_PREFIX) and suffix in PACKAGE_SUFFIXES:
            destination_name = path.name
        elif path.name in UPDATE_METADATA_NAMES:
            destination_name = f'{platform_id}-{path.name}'
        else:
            continue
        destination = output / destination_name
        if destination.exists():
            raise RuntimeError(
                f'Duplicate collected release asset name for {platform_id}: '
                f'{destination_name}'
            )
        copy(path, destination)
        copied.append(destination_name)

    evidence_root = app_root / 'release-evidence'
    for path in sorted(evidence_root.glob('*')):
        if not path.is_file():
            continue
        destination = output / f'{platform_id}-{path.name}'
        if destination.exists():
            raise RuntimeError(f'Duplicate release evidence name: {destination.name}')
        copy(path, destination)
        copied.append(destination.name)

    smoke = app_root / 'packaged-smoke-evidence.json'
    if not smoke.is_file():
        raise RuntimeError('Packaged application smoke evidence is missing.')
    smoke_destination = output / f'{platform_id}-packaged-smoke-evidence.json'
    copy(smoke, smoke_destination)
    copied.append(smoke_destination.name)

    engine_manifest = app_root / 'engine-bin' / 'mel-engine' / 'engine-build-manifest.json'
    if not engine_manifest.is_file():
        raise RuntimeError('Self-contained engine build manifest is missing.')
    engine_destination = output / f'{platform_id}-engine-build-manifest.json'
    copy(engine_manifest, engine_destination)
    copied.append(engine_destination.name)

    package_count = sum(name.startswith(PACKAGE_PREFIX) for name in copied)
    if package_count == 0:
        raise RuntimeError(f'No top-level application packages were collected for {platform_id}.')
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform-id', required=True)
    args = parser.parse_args()
    app_root = Path(__file__).resolve().parents[1]
    copied = collect_platform_artifacts(app_root, args.platform_id)
    print(f'Collected {len(copied)} allowlisted files for {args.platform_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
