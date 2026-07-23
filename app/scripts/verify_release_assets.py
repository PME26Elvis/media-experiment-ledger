from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def expected_package_names(version: str) -> list[str]:
    stem = f'Media-Experiment-Ledger-Studio-{version}'
    return [
        f'{stem}-windows-x64-setup.exe',
        f'{stem}-windows-x64-portable.exe',
        f'{stem}-macos-arm64.dmg',
        f'{stem}-macos-arm64.zip',
        f'{stem}-macos-x64.dmg',
        f'{stem}-macos-x64.zip',
        f'{stem}-linux-x86_64.AppImage',
        f'{stem}-linux-amd64.deb',
    ]


def expected_evidence_names() -> list[str]:
    platform_ids = ['windows-x64', 'linux-x64', 'macos-arm64', 'macos-x64']
    return [
        *(f'{platform}-engine-build-manifest.json' for platform in platform_ids),
        *(f'{platform}-packaged-smoke-evidence.json' for platform in platform_ids),
    ]


def verify(root: Path, plan: dict[str, Any], *, minimum_package_bytes: int = 1_000_000) -> dict[str, Any]:
    root = root.resolve()
    names = [path.name for path in root.rglob('*') if path.is_file()]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RuntimeError(f'Duplicate release asset names: {duplicates}')

    packages = expected_package_names(str(plan['version']))
    evidence = expected_evidence_names()
    missing = [name for name in [*packages, *evidence] if name not in names]
    if missing:
        raise RuntimeError(f'Missing required Studio release assets: {missing}')

    undersized: list[str] = []
    for name in packages:
        path = next(path for path in root.rglob(name) if path.is_file())
        if path.stat().st_size < minimum_package_bytes:
            undersized.append(f'{name} ({path.stat().st_size} bytes)')
    if undersized:
        raise RuntimeError(f'Package assets are unexpectedly small: {undersized}')

    smoke_failures: list[str] = []
    for name in (item for item in evidence if item.endswith('packaged-smoke-evidence.json')):
        path = next(path for path in root.rglob(name) if path.is_file())
        payload = json.loads(path.read_text(encoding='utf-8'))
        expected = {
            'packaged': True,
            'rendererLoaded': True,
            'preloadBridge': True,
            'engineReady': True,
        }
        failed = [key for key, value in expected.items() if payload.get(key) is not value]
        database = payload.get('database')
        if not isinstance(database, dict) or database.get('ok') is not True:
            failed.append('database.ok')
        if failed:
            smoke_failures.append(f'{name}: {failed}')
    if smoke_failures:
        raise RuntimeError(f'Packaged launch evidence failed: {smoke_failures}')

    return {
        'schema_version': 1,
        'version': plan['version'],
        'package_count': len(packages),
        'evidence_count': len(evidence),
        'packages': packages,
        'evidence': evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--minimum-package-bytes', type=int, default=1_000_000)
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    result = verify(
        Path(args.root), plan, minimum_package_bytes=args.minimum_package_bytes
    )
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
