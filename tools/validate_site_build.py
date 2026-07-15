#!/usr/bin/env python3
"""Validate GitHub Pages routes and base-prefixed data artifacts after Astro build."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE = "/media-experiment-ledger/"
PRIMARY_ROUTES = ("overview", "analytics", "forecast", "architecture", "frontend-stack")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(root: Path) -> None:
    errors: list[str] = []
    require(root.is_dir(), f"Missing site output directory: {root}", errors)

    pages: dict[str, str] = {}
    for route in PRIMARY_ROUTES:
        path = root / route / "index.html"
        require(path.is_file(), f"Missing primary route output: {path}", errors)
        if path.is_file():
            pages[route] = path.read_text(encoding="utf-8")

    overview = pages.get("overview", "")
    for route in PRIMARY_ROUTES:
        expected = f'href="{BASE}{route}/"'
        require(expected in overview, f"Overview is missing base-safe link: {expected}", errors)

    analytics_url = f'data-analytics-url="{BASE}data/analytics.json"'
    forecast_url = f'data-forecast-url="{BASE}data/forecast.json"'
    require(analytics_url in pages.get("analytics", ""), f"Missing analytics artifact URL: {analytics_url}", errors)
    require(forecast_url in pages.get("forecast", ""), f"Missing forecast artifact URL: {forecast_url}", errors)

    malformed = (
        "/media-experiment-ledgeroverview/",
        "/media-experiment-ledgeranalytics/",
        "/media-experiment-ledgerforecast/",
        "/media-experiment-ledgerarchitecture/",
        "/media-experiment-ledgerfrontend-stack/",
        "/media-experiment-ledgerdata/",
    )
    for route, html in pages.items():
        for fragment in malformed:
            require(fragment not in html, f"Malformed base path in {route}: {fragment}", errors)

    for name in ("analytics", "forecast"):
        path = root / "data" / f"{name}.json"
        require(path.is_file(), f"Missing deployed artifact: {path}", errors)
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                require(isinstance(payload, dict), f"Artifact is not a JSON object: {path}", errors)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON in {path}: {exc}")

    if errors:
        raise SystemExit("Site validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {len(PRIMARY_ROUTES)} routes and two data artifacts under {BASE}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    args = parser.parse_args()
    validate(args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
