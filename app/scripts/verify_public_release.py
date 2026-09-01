from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from verify_release_assets import expected_evidence_names, expected_package_names


def evidence_bundle_name(version: str) -> str:
    return f'Media-Experiment-Ledger-Studio-{version}-evidence.zip'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, separator, name = line.partition('  ')
        if not separator or len(digest) != 64 or not name:
            raise RuntimeError(f'Invalid SHA256SUMS line: {line!r}')
        if name in result:
            raise RuntimeError(f'Duplicate checksum entry: {name}')
        result[name] = digest
    return result


def verify_public(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    version = str(plan['version'])
    bundle = evidence_bundle_name(version)
    required = set(expected_package_names(version)) | {
        bundle,
        'RELEASE_NOTES.md',
        'release-verification.json',
        'release-manifest.json',
        'SHA256SUMS',
    }
    optional = {'SHA256SUMS.asc'}
    actual = {path.name for path in root.iterdir() if path.is_file()}
    missing = sorted(required - actual)
    unexpected = sorted(actual - required - optional)
    if missing:
        raise RuntimeError(f'Missing finalized public Release assets: {missing}')
    if unexpected:
        raise RuntimeError(f'Unexpected finalized public Release assets: {unexpected}')

    verification = json.loads((root / 'release-verification.json').read_text(encoding='utf-8'))
    if verification.get('package_count') != 8:
        raise RuntimeError('release-verification.json does not record eight packages.')
    if verification.get('evidence_bundle') != bundle:
        raise RuntimeError('release-verification.json references the wrong evidence bundle.')
    if verification.get('public_asset_policy') != 'eight_packages_plus_consolidated_evidence':
        raise RuntimeError('Unexpected public asset policy.')

    with zipfile.ZipFile(root / bundle) as archive:
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise RuntimeError('Evidence bundle contains duplicate member names.')
        if any(name.startswith('/') or '..' in Path(name).parts for name in members):
            raise RuntimeError('Evidence bundle contains an unsafe path.')
        expected_evidence = set(expected_evidence_names())
        if set(members) != expected_evidence:
            raise RuntimeError(
                'Evidence bundle contents do not match the exact expected set: '
                f'missing={sorted(expected_evidence - set(members))}, '
                f'unexpected={sorted(set(members) - expected_evidence)}'
            )

    manifest = json.loads((root / 'release-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 3:
        raise RuntimeError('Unsupported release manifest schema.')
    if manifest.get('source_sha') != plan.get('source_sha'):
        raise RuntimeError('Release manifest source SHA does not match the plan.')
    if manifest.get('version') != version:
        raise RuntimeError('Release manifest version does not match the plan.')

    checksummed_names = required - {'release-manifest.json', 'SHA256SUMS'}
    manifest_entries = manifest.get('assets')
    if not isinstance(manifest_entries, list):
        raise RuntimeError('Release manifest assets are missing.')
    manifest_by_name = {str(entry.get('name')): entry for entry in manifest_entries}
    if set(manifest_by_name) != checksummed_names:
        raise RuntimeError('Release manifest does not describe the exact checksummed public set.')

    checksum_entries = parse_checksums(root / 'SHA256SUMS')
    if set(checksum_entries) != checksummed_names:
        raise RuntimeError('SHA256SUMS does not describe the exact checksummed public set.')

    for name in sorted(checksummed_names):
        path = root / name
        digest = sha256(path)
        if checksum_entries[name] != digest:
            raise RuntimeError(f'Checksum mismatch for {name}.')
        entry = manifest_by_name[name]
        if entry.get('sha256') != digest or entry.get('size_bytes') != path.stat().st_size:
            raise RuntimeError(f'Manifest mismatch for {name}.')

    return {
        'schema_version': 1,
        'version': version,
        'source_sha': plan.get('source_sha'),
        'public_asset_count': len(actual),
        'checksummed_asset_count': len(checksummed_names),
        'evidence_member_count': len(expected_evidence_names()),
        'clean_public_asset_set': True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    result = verify_public(Path(args.root), plan)
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
