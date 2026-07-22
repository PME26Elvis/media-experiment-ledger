from __future__ import annotations

import argparse
import re
from pathlib import Path


def features(value: str) -> list[str]:
    return [
        item.strip(' -\t')
        for item in re.split(r'[\n,]+', value)
        if item.strip(' -\t')
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', required=True)
    parser.add_argument('--notes', default='')
    parser.add_argument('--features', default='')
    parser.add_argument('--quick-start-tag', default='')
    parser.add_argument('--full-research-tag', default='')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    lines = [
        f'# Media Experiment Ledger Studio {args.version}',
        '',
        f'Channel: **{args.channel}**',
        '',
    ]
    if args.notes.strip():
        lines += [args.notes.strip(), '']
    selected = features(args.features)
    if selected:
        lines += ['## Features and fixes', '']
        lines += [f'- {item}' for item in selected]
        lines.append('')
    lines += [
        '## Desktop packages',
        '',
        '- Windows x64 NSIS installer and portable package',
        '- macOS Apple Silicon DMG/update ZIP',
        '- macOS Intel x64 DMG/update ZIP',
        '- Linux x64 AppImage and `.deb`',
        '',
        '## Sample corpus compatibility',
        '',
        f'- Quick Start: `{args.quick_start_tag or "not pinned"}`',
        f'- Full Research: `{args.full_research_tag or "not pinned"}`',
        '',
        '## Verification evidence',
        '',
        '- SHA-256 asset checksums and signed checksum file',
        '- Release asset manifest',
        '- CycloneDX SBOM',
        '- Third-party notices',
        '- Per-platform self-contained engine build manifests',
        '',
        'Model weights and sample data retain separate rights manifests and are not licensed merely by the Apache-2.0 application source license.',
        '',
    ]
    Path(args.output).write_text('\n'.join(lines), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
