from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PLATFORM_IDS = ['windows-x64', 'linux-x64', 'macos-arm64', 'macos-x64']
PLATFORM_EVIDENCE_BASENAMES = [
    'engine-build-manifest.json',
    'packaged-smoke-evidence.json',
    'sbom.cdx.json',
    'third-party-notices.json',
    'build-input-manifest.json',
]
UPDATE_METADATA = {
    'windows-x64': 'latest.yml',
    'linux-x64': 'latest-linux.yml',
    'macos-arm64': 'latest-mac.yml',
    'macos-x64': 'latest-mac.yml',
}


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
    result = [
        f'{platform}-{basename}'
        for platform in PLATFORM_IDS
        for basename in PLATFORM_EVIDENCE_BASENAMES
    ]
    result.extend(
        f'{platform}-{metadata}' for platform, metadata in UPDATE_METADATA.items()
    )
    return result


def evidence_bundle_name(version: str) -> str:
    return f'Media-Experiment-Ledger-Studio-{version}-evidence.zip'


def verify(root: Path, plan: dict[str, Any], *, minimum_package_bytes: int = 1_000_000) -> dict[str, Any]:
    root = root.resolve()
    names = [path.name for path in root.iterdir() if path.is_file()]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RuntimeError(f'Duplicate release asset names: {duplicates}')

    packages = expected_package_names(str(plan['version']))
    evidence = expected_evidence_names()
    expected = set(packages) | set(evidence) | {'RELEASE_NOTES.md'}
    actual = set(names)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        raise RuntimeError(f'Missing required Studio release assets: {missing}')
    if unexpected:
        raise RuntimeError(
            'Unexpected pre-publication assets are blocked from the public Release: '
            f'{unexpected}'
        )

    undersized: list[str] = []
    for name in packages:
        path = root / name
        if path.stat().st_size < minimum_package_bytes:
            undersized.append(f'{name} ({path.stat().st_size} bytes)')
    if undersized:
        raise RuntimeError(f'Package assets are unexpectedly small: {undersized}')

    smoke_failures: list[str] = []
    for name in (item for item in evidence if item.endswith('packaged-smoke-evidence.json')):
        payload = json.loads((root / name).read_text(encoding='utf-8'))
        expected_smoke = {
            'packaged': True,
            'rendererLoaded': True,
            'preloadBridge': True,
            'engineReady': True,
        }
        failed = [key for key, value in expected_smoke.items() if payload.get(key) is not value]
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
        'prepublication_asset_count': len(expected),
        'unexpected_assets_blocked': True,
    }


def finalized_bundle_exists(root: Path, plan: dict[str, Any]) -> bool:
    return (root / evidence_bundle_name(str(plan['version']))).is_file()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--minimum-package-bytes', type=int, default=1_000_000)
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))

    if finalized_bundle_exists(root, plan):
        from verify_public_release import verify_public

        result = verify_public(root, plan)
        # The finalizer created release-verification.json before checksums and the
        # release manifest. Rewriting that file here would invalidate both. When
        # the workflow passes the same output path, verify it exists and preserve it.
        if args.output:
            output = Path(args.output).resolve()
            if output != root / 'release-verification.json':
                output.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8',
                )
            elif not output.is_file():
                raise RuntimeError('Finalized release-verification.json is missing.')
    else:
        result = verify(root, plan, minimum_package_bytes=args.minimum_package_bytes)
        if args.output:
            Path(args.output).write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
            )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
