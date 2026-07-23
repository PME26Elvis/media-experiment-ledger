from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SEMVER = re.compile(
    r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    r'(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$'
)
CHANNELS = {'alpha', 'beta', 'stable'}
TAG_PREFIX = 'studio-v'
TAIPEI_TIMEZONE = timezone(timedelta(hours=8), name='Asia/Taipei')


def parse_bool(value: Any, *, default: bool) -> bool:
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ValueError(f'Invalid boolean value: {value!r}')


def normalize_features(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = [str(item) for item in value]
    else:
        raw = re.split(r'[\n,]+', str(value))
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        normalized = item.strip(' -\t')
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def read_existing_tags(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    tags: set[str] = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith('refs/tags/'):
            value = value.removeprefix('refs/tags/')
        tags.add(value)
    return tags


def semver_base(version: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError(f'Invalid package SemVer: {version}')
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def validate_explicit_version(version: str, channel: str) -> None:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError(f'Invalid SemVer: {version}')
    prerelease = match.group(4) or ''
    if channel == 'stable' and prerelease:
        raise ValueError('Stable releases must not contain a prerelease suffix.')
    if channel in {'alpha', 'beta'} and not prerelease.startswith(f'{channel}.'):
        raise ValueError(
            f'{channel} releases must use a matching -{channel}.N prerelease suffix, or version=auto.'
        )


def resolve_version(
    requested: str,
    *,
    channel: str,
    package_version: str,
    existing_tags: set[str],
) -> tuple[str, str]:
    requested = requested.strip()
    if requested and requested.lower() != 'auto':
        validate_explicit_version(requested, channel)
        tag = f'{TAG_PREFIX}{requested}'
        if tag in existing_tags:
            raise ValueError(f'Release tag already exists and will not be modified: {tag}')
        return requested, 'explicit'

    major, minor, patch = semver_base(package_version)
    base = f'{major}.{minor}.{patch}'
    if channel in {'alpha', 'beta'}:
        pattern = re.compile(
            rf'^{re.escape(TAG_PREFIX + base + "-" + channel + ".")}(\d+)$'
        )
        used = [int(match.group(1)) for tag in existing_tags if (match := pattern.fullmatch(tag))]
        sequence = max(used, default=0) + 1
        return f'{base}-{channel}.{sequence}', 'auto-prerelease'

    candidate = base
    while f'{TAG_PREFIX}{candidate}' in existing_tags:
        patch += 1
        candidate = f'{major}.{minor}.{patch}'
    return candidate, 'auto-stable-patch'


def build_plan(
    request: dict[str, Any],
    *,
    package_version: str,
    existing_tags: set[str],
    source_sha: str,
    overrides: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if int(request.get('schema_version', 1)) != 1:
        raise ValueError('Unsupported release-request schema_version.')
    overrides = overrides or {}

    def selected(name: str, default: Any = '') -> Any:
        override = overrides.get(name)
        return request.get(name, default) if override is None or override == '' else override

    channel = str(selected('channel', 'beta')).strip().lower()
    if channel not in CHANNELS:
        raise ValueError(f'Unsupported release channel: {channel}')
    version, version_origin = resolve_version(
        str(selected('version', 'auto')),
        channel=channel,
        package_version=package_version,
        existing_tags=existing_tags,
    )
    tag = f'{TAG_PREFIX}{version}'
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    instant = instant.astimezone(timezone.utc)
    taipei = instant.astimezone(TAIPEI_TIMEZONE)

    plan = {
        'schema_version': 1,
        'product': 'Media Experiment Ledger Studio',
        'source_branch': str(request.get('source_branch') or 'app-main'),
        'source_sha': source_sha,
        'version': version,
        'version_origin': version_origin,
        'tag': tag,
        'channel': channel,
        'prerelease': channel != 'stable',
        'draft': parse_bool(selected('draft', True), default=True),
        'publish': parse_bool(selected('publish', False), default=False),
        'release_notes': str(selected('release_notes', '')).strip(),
        'features': normalize_features(selected('features', [])),
        'quick_start_tag': str(selected('quick_start_tag', '')).strip(),
        'full_research_tag': str(selected('full_research_tag', '')).strip(),
        'generated_at_utc': instant.isoformat().replace('+00:00', 'Z'),
        'release_date_taipei': taipei.date().isoformat(),
        'release_time_taipei': taipei.isoformat(),
        'stable_qualification_required': channel == 'stable',
    }
    return plan


def write_github_outputs(path: Path, plan: dict[str, Any]) -> None:
    values = {
        'version': plan['version'],
        'tag': plan['tag'],
        'channel': plan['channel'],
        'draft': str(plan['draft']).lower(),
        'publish': str(plan['publish']).lower(),
        'source_sha': plan['source_sha'],
        'release_date_taipei': plan['release_date_taipei'],
    }
    with path.open('a', encoding='utf-8') as stream:
        for key, value in values.items():
            stream.write(f'{key}={value}\n')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--existing-tags', required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--version-override', default='')
    parser.add_argument('--channel-override', default='')
    parser.add_argument('--notes-override', default='')
    parser.add_argument('--features-override', default='')
    parser.add_argument('--quick-start-tag-override', default='')
    parser.add_argument('--full-research-tag-override', default='')
    parser.add_argument('--draft-override', default='')
    parser.add_argument('--publish-override', default='')
    parser.add_argument('--output', required=True)
    parser.add_argument('--github-output', default='')
    args = parser.parse_args()

    request_path = Path(args.request)
    request = json.loads(request_path.read_text(encoding='utf-8')) if request_path.is_file() else {}
    package = json.loads(Path(args.package).read_text(encoding='utf-8'))
    plan = build_plan(
        request,
        package_version=str(package['version']),
        existing_tags=read_existing_tags(Path(args.existing_tags)),
        source_sha=args.source_sha,
        overrides={
            'version': args.version_override,
            'channel': args.channel_override,
            'release_notes': args.notes_override,
            'features': args.features_override,
            'quick_start_tag': args.quick_start_tag_override,
            'full_research_tag': args.full_research_tag_override,
            'draft': args.draft_override,
            'publish': args.publish_override,
        },
    )
    Path(args.output).write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    if args.github_output:
        write_github_outputs(Path(args.github_output), plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
