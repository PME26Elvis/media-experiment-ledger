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
    mode: str = 'execution',
) -> list[str]:
    provider = PROVIDERS[provider_key]
    available = manifest.get('provider_inventory', {}).get('available_providers', [])
    failures: list[str] = []

    if provider not in available:
        failures.append(f'packaged engine missing qualified provider {provider}: {available}')
    if evidence.get('provider') not in {None, provider}:
        failures.append(f"evidence provider mismatch: {evidence.get('provider')} != {provider}")
    if evidence.get('available') is False:
        failures.append(f'provider runtime inventory did not expose {provider}')

    target = evidence.get('target')
    assigned_nodes = target.get('assigned_node_count', 0) if isinstance(target, dict) else 0
    comparison = evidence.get('comparison')
    comparison_passed = comparison.get('passed') if isinstance(comparison, dict) else False

    if mode == 'inventory':
        if evidence.get('status') != 'executed':
            failures.append(f"provider inventory probe did not execute a comparison: {evidence.get('status')}")
        if not comparison_passed:
            failures.append(f'provider inventory probe comparison failed: {comparison or evidence.get("error")}')
        if qualification_outcome not in {'success', 'failure'}:
            failures.append(f'unsupported qualification command outcome={qualification_outcome}')
        return failures

    if qualification_outcome != 'success':
        failures.append(f'qualification command outcome={qualification_outcome}')
    if not evidence.get('passed'):
        failures.append(f"provider evidence failed: {evidence.get('error') or comparison}")
    if assigned_nodes <= 0:
        failures.append(f'provider did not execute graph nodes: {target}')
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=sorted(PROVIDERS), required=True)
    parser.add_argument('--mode', choices=['execution', 'inventory'], default='execution')
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
        mode=args.mode,
    )
    if failures:
        raise SystemExit('\n'.join(failures))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
