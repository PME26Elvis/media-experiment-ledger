from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDERS = {
    'cpu': 'CPUExecutionProvider',
    'directml': 'DmlExecutionProvider',
    'coreml': 'CoreMLExecutionProvider',
    'cuda': 'CUDAExecutionProvider',
}


def enforce(
    *,
    provider_key: str,
    qualification_outcome: str,
    evidence: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    provider = PROVIDERS[provider_key]
    available = manifest.get('provider_inventory', {}).get('available_providers', [])
    failures: list[str] = []
    if qualification_outcome != 'success':
        failures.append(f'qualification command outcome={qualification_outcome}')
    if provider not in available:
        failures.append(f'packaged engine missing qualified provider {provider}: {available}')
    if not evidence.get('passed'):
        failures.append(f"provider evidence failed: {evidence.get('error') or evidence.get('comparison')}")
    target = evidence.get('target')
    assigned_nodes = target.get('assigned_node_count', 0) if isinstance(target, dict) else 0
    if assigned_nodes <= 0:
        failures.append(f'provider did not execute graph nodes: {target}')
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=sorted(PROVIDERS), required=True)
    parser.add_argument('--qualification-outcome', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--command-log', type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.evidence.is_file():
        if args.command_log and args.command_log.is_file():
            print(args.command_log.read_text(encoding='utf-8', errors='replace'))
        raise SystemExit(f'provider evidence was not written: {args.evidence}')
    evidence = json.loads(args.evidence.read_text(encoding='utf-8'))
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    print(json.dumps(evidence, indent=2))
    failures = enforce(
        provider_key=args.provider,
        qualification_outcome=args.qualification_outcome,
        evidence=evidence,
        manifest=manifest,
    )
    if failures:
        raise SystemExit('\n'.join(failures))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
