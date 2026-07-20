#!/usr/bin/env python3
"""Apply the one-time migration from a same-repository PR validation run."""
from __future__ import annotations

from pathlib import Path

import apply_contract_sync as sync

ROOT = Path(__file__).resolve().parents[1]

FINAL_VALIDATE = '''name: Validate ledger tooling

on:
  pull_request:
    paths:
      - "tools/**"
      - "tests/**"
      - "web/**"
      - "README.md"
      - "README.en.md"
      - "AGENTS.md"
      - "project-contract.json"
      - "config/**"
      - "docs/**"
      - "requirements-analytics.txt"
      - "requirements-forecast.txt"
      - "requirements-visual-analysis.txt"
      - ".github/workflows/**"
  push:
    branches: [main]
    paths:
      - "tools/**"
      - "tests/**"
      - "web/**"
      - "README.md"
      - "README.en.md"
      - "AGENTS.md"
      - "project-contract.json"
      - "config/**"
      - "docs/**"
      - "requirements-analytics.txt"
      - "requirements-forecast.txt"
      - "requirements-visual-analysis.txt"
      - ".github/workflows/**"

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            requirements-analytics.txt
            requirements-forecast.txt
            requirements-visual-analysis.txt
      - name: Install Python and FFmpeg test dependencies
        run: |
          set -euo pipefail
          python -m pip install \\
            -r requirements-analytics.txt \\
            -r requirements-forecast.txt \\
            -r requirements-visual-analysis.txt
          sudo apt-get update -qq
          sudo apt-get install -y --no-install-recommends ffmpeg
          ffmpeg -version | head -n 1
          ffprobe -version | head -n 1
      - name: Validate synchronized project contract
        run: python tools/validate_project_contract.py
      - run: python -m compileall tools tests
      - run: python -m unittest discover -s tests -v
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
      - name: Install web dependencies
        run: npm install --prefix web --package-lock=false --no-audit --no-fund
      - name: Build production Pages site
        run: npm run build --prefix web
      - name: Validate Pages routes and artifact URLs
        run: python tools/validate_site_build.py
'''


def main() -> None:
    sync.patch_release_packaging()
    sync.patch_release_publishing()
    sync.patch_analytics()
    sync.patch_atlas_data()
    sync.patch_readme_summary()
    sync.patch_readmes_and_agents()
    sync.patch_specs()
    sync.write_tests()

    # Workflow path triggers needed after policy changes.
    sync.replace_once(
        ".github/workflows/visual-analysis.yml",
        "      - 'tools/release_publishing.py'\n",
        "      - 'tools/release_publishing.py'\n"
        "      - 'tools/release_policy.py'\n"
        "      - 'config/release-quarantine.json'\n"
        "      - 'project-contract.json'\n",
    )
    sync.replace_once(
        ".github/workflows/analytics.yml",
        '      - "tools/forecast_*.py"\n',
        '      - "tools/forecast_*.py"\n'
        '      - "tools/analyze_releases.py"\n'
        '      - "tools/release_policy.py"\n'
        '      - "config/release-quarantine.json"\n'
        '      - "project-contract.json"\n',
    )
    sync.replace_once(
        ".github/workflows/analytics.yml",
        '''          if [[ "$EVENT_NAME" == "release" ]]; then
            args+=(--mode exact_tag --exact-tag "$EVENT_TAG")
          else
            mode="${INPUT_MODE:-new_only}"
''',
        '''          if [[ "$EVENT_NAME" == "release" ]]; then
            args+=(--mode exact_tag --exact-tag "$EVENT_TAG")
          elif [[ "$EVENT_NAME" == "push" ]]; then
            # Contract, quarantine, or analytics-code changes must rebuild the
            # complete canonical corpus rather than retaining polluted state.
            args+=(--mode rebuild_all)
          else
            mode="${INPUT_MODE:-new_only}"
''',
    )

    (ROOT / ".github" / "workflows" / "validate.yml").write_text(
        FINAL_VALIDATE,
        encoding="utf-8",
    )
    for path in (
        ROOT / "tools" / "apply_contract_sync.py",
        ROOT / "tools" / "finalize_contract_sync.py",
        ROOT / ".github" / "workflows" / "contract-sync-bootstrap.yml",
    ):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
