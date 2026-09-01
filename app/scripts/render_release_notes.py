from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def features(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = [str(item) for item in value]
    else:
        raw = re.split(r'[\n,]+', str(value or ''))
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        normalized = item.strip(' -\t')
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def render(plan: dict[str, Any]) -> str:
    version = str(plan['version'])
    channel = str(plan['channel'])
    selected = features(plan.get('features', []))
    lines = [
        f'# Media Experiment Ledger Studio {version}',
        '',
        f'Channel: **{channel}**',
        '',
        f'Published for Taipei date: **{plan.get("release_date_taipei", "unknown")}**',
        '',
        f'Source commit: `{plan.get("source_sha", "unknown")}`',
        '',
    ]
    if channel != 'stable':
        lines += [
            '> [!IMPORTANT]',
            '> This is a prerelease build for validation. Windows or macOS may show an',
            '> unsigned-publisher warning when signing credentials are not configured.',
            '> Verify downloaded files against `SHA256SUMS` before installation.',
            '',
        ]
    notes = str(plan.get('release_notes') or '').strip()
    if notes:
        lines += [notes, '']
    if selected:
        lines += ['## Features and fixes', '']
        lines += [f'- {item}' for item in selected]
        lines.append('')
    lines += [
        '## Desktop packages',
        '',
        '- Windows x64 NSIS installer',
        '- Windows x64 portable package',
        '- macOS Apple Silicon arm64 DMG and update ZIP',
        '- macOS Intel x64 DMG and update ZIP',
        '- Linux x64 AppImage and `.deb`',
        '',
        '## Sample corpus compatibility',
        '',
        f'- Quick Start: `{plan.get("quick_start_tag") or "not pinned in this release"}`',
        f'- Full Research: `{plan.get("full_research_tag") or "not pinned in this release"}`',
        '',
        'Sample corpora are independent immutable Releases and are not silently bundled',
        'into the application packages.',
        '',
        '## Verification evidence',
        '',
        '- SHA-256 checksum manifest for every published asset',
        '- Detached GPG checksum signature when signing keys are configured; mandatory for stable releases',
        '- Release asset manifest with UTC timestamp and Taipei release date',
        '- CycloneDX SBOM and third-party notices',
        '- Per-platform self-contained engine build manifests',
        '- Per-platform packaged application launch evidence',
        '',
        '## Qualification boundary',
        '',
        '- Hosted CI validates CPU execution and packaged startup on Windows, macOS and Linux.',
        '- DirectML, CUDA and CoreML claims require separate real-hardware evidence.',
        '- Stable automatic updates require platform signing and Apple notarization.',
        '',
        'Model weights and sample data retain separate rights manifests and are not licensed merely by the Apache-2.0 application source license.',
        '',
    ]
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default='')
    parser.add_argument('--version', default='')
    parser.add_argument('--channel', default='beta')
    parser.add_argument('--notes', default='')
    parser.add_argument('--features', default='')
    parser.add_argument('--quick-start-tag', default='')
    parser.add_argument('--full-research-tag', default='')
    parser.add_argument('--source-sha', default='')
    parser.add_argument('--release-date-taipei', default='')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    if args.plan:
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    else:
        if not args.version:
            parser.error('--version is required when --plan is not supplied')
        plan = {
            'version': args.version,
            'channel': args.channel,
            'release_notes': args.notes,
            'features': features(args.features),
            'quick_start_tag': args.quick_start_tag,
            'full_research_tag': args.full_research_tag,
            'source_sha': args.source_sha,
            'release_date_taipei': args.release_date_taipei,
        }
    Path(args.output).write_text(render(plan), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
