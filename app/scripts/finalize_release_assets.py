from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verify_release_assets import verify

EXCLUDED = {
    'SHA256SUMS',
    'SHA256SUMS.asc',
    'release-manifest.json',
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    files = [
        path for path in root.rglob('*')
        if path.is_file() and path.name not in EXCLUDED
    ]
    entries = [
        {
            'path': path.relative_to(root).as_posix(),
            'name': path.name,
            'size_bytes': path.stat().st_size,
            'sha256': sha256(path),
        }
        for path in sorted(files)
    ]
    return {
        'schema_version': 2,
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
    verification = verify(
        root,
        plan,
        minimum_package_bytes=minimum_package_bytes,
    )
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
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
