from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verify_release_assets import expected_package_names, verify

GENERATED_NAMES = {
    'SHA256SUMS',
    'SHA256SUMS.asc',
    'release-manifest.json',
    'release-verification.json',
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_bundle_name(version: str) -> str:
    return f'Media-Experiment-Ledger-Studio-{version}-evidence.zip'


def write_deterministic_zip(path: Path, files: list[Path], root: Path) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(files, key=lambda item: item.name):
            relative = source.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def build_manifest(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    files = [
        path for path in root.iterdir()
        if path.is_file() and path.name not in {'SHA256SUMS', 'SHA256SUMS.asc', 'release-manifest.json'}
    ]
    entries = [
        {
            'path': path.name,
            'name': path.name,
            'size_bytes': path.stat().st_size,
            'sha256': sha256(path),
        }
        for path in sorted(files)
    ]
    return {
        'schema_version': 3,
        'product': 'Media Experiment Ledger Studio',
        'version': plan['version'],
        'tag': plan.get('tag') or f"studio-v{plan['version']}",
        'channel': plan['channel'],
        'prerelease': bool(plan.get('prerelease', plan['channel'] != 'stable')),
        'draft': bool(plan.get('draft', False)),
        'source_branch': plan.get('source_branch', 'app-main'),
        'source_sha': plan.get('source_sha') or plan.get('git_sha'),
        'release_date_taipei': plan.get('release_date_taipei'),
        'planned_at_utc': plan.get('generated_at_utc'),
        'finalized_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'sample_corpora': {
            'quick_start': plan.get('quick_start_tag') or None,
            'full_research': plan.get('full_research_tag') or None,
        },
        'public_asset_policy': 'eight_packages_plus_consolidated_evidence',
        'asset_count': len(entries),
        'total_bytes': sum(entry['size_bytes'] for entry in entries),
        'assets': entries,
    }


def finalize(
    root: Path,
    plan: dict[str, Any],
    *,
    minimum_package_bytes: int = 1_000_000,
) -> dict[str, Any]:
    root = root.resolve()
    for name in GENERATED_NAMES | {evidence_bundle_name(str(plan['version']))}:
        (root / name).unlink(missing_ok=True)

    verification = verify(
        root,
        plan,
        minimum_package_bytes=minimum_package_bytes,
    )
    package_names = set(expected_package_names(str(plan['version'])))
    notes_name = 'RELEASE_NOTES.md'
    if not (root / notes_name).is_file():
        raise RuntimeError('RELEASE_NOTES.md must exist before release finalization.')

    evidence_files = [
        path for path in root.iterdir()
        if path.is_file() and path.name not in package_names | {notes_name}
    ]
    if not evidence_files:
        raise RuntimeError('No release evidence files were available to bundle.')
    bundle_name = evidence_bundle_name(str(plan['version']))
    bundle_path = root / bundle_name
    write_deterministic_zip(bundle_path, evidence_files, root)
    for path in evidence_files:
        path.unlink()

    verification.update({
        'schema_version': 2,
        'evidence_bundle': bundle_name,
        'bundled_evidence_count': len(evidence_files),
        'public_asset_policy': 'eight_packages_plus_consolidated_evidence',
    })
    (root / 'release-verification.json').write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    manifest = build_manifest(root, plan)
    checksums = '\n'.join(
        f"{entry['sha256']}  {entry['path']}" for entry in manifest['assets']
    ) + '\n'
    (root / 'SHA256SUMS').write_text(checksums, encoding='utf-8')
    (root / 'release-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--plan', default='')
    parser.add_argument('--version', default='')
    parser.add_argument('--channel', default='beta')
    parser.add_argument('--git-sha', default='')
    parser.add_argument('--quick-start-tag', default='')
    parser.add_argument('--full-research-tag', default='')
    parser.add_argument('--minimum-package-bytes', type=int, default=1_000_000)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.plan:
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    else:
        if not args.version or not args.git_sha:
            parser.error('--version and --git-sha are required when --plan is not supplied')
        plan = {
            'version': args.version,
            'channel': args.channel,
            'git_sha': args.git_sha,
            'quick_start_tag': args.quick_start_tag,
            'full_research_tag': args.full_research_tag,
        }
    manifest = finalize(
        root,
        plan,
        minimum_package_bytes=args.minimum_package_bytes,
    )
    print(json.dumps({
        'assets': manifest['asset_count'],
        'bytes': manifest['total_bytes'],
        'source_sha': manifest['source_sha'],
        'release_date_taipei': manifest['release_date_taipei'],
        'public_asset_policy': manifest['public_asset_policy'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
