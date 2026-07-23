from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', required=True)
    parser.add_argument('--git-sha', required=True)
    parser.add_argument('--quick-start-tag', default='')
    parser.add_argument('--full-research-tag', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
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
    checksums = '\n'.join(
        f"{entry['sha256']}  {entry['path']}" for entry in entries
    ) + '\n'
    (root / 'SHA256SUMS').write_text(checksums, encoding='utf-8')
    manifest = {
        'schema_version': 1,
        'product': 'Media Experiment Ledger Studio',
        'version': args.version,
        'channel': args.channel,
        'git_sha': args.git_sha,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'sample_corpora': {
            'quick_start': args.quick_start_tag or None,
            'full_research': args.full_research_tag or None,
        },
        'asset_count': len(entries),
        'total_bytes': sum(entry['size_bytes'] for entry in entries),
        'assets': entries,
    }
    (root / 'release-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(json.dumps({
        'assets': len(entries),
        'bytes': manifest['total_bytes'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
