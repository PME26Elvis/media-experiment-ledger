#!/usr/bin/env python3
"""Validate GitHub Pages routes, base-prefixed data artifacts, and build size."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE = "/media-experiment-ledger/"
PRIMARY_ROUTES = (
    "overview",
    "analytics",
    "visual-lab",
    "yolo-lab",
    "forecast",
    "architecture",
    "frontend-stack",
)
DATA_ARTIFACTS = (
    ("analytics", Path("data/analytics.json"), "analytics", "data-analytics-url"),
    ("forecast", Path("data/forecast.json"), "forecast", "data-forecast-url"),
    ("visual-analysis", Path("data/visual-analysis.json"), "visual-lab", "data-url"),
    ("yolo", Path("data/yolo/latest.json"), "yolo-lab", "data-url"),
)
MAX_SITE_BYTES = 1_000_000_000
MAX_FILE_BYTES = 100_000_000


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

    for name, relative_path, route, attribute in DATA_ARTIFACTS:
        expected = f'{attribute}="{BASE}{relative_path.as_posix()}"'
        require(
            expected in pages.get(route, ""),
            f"Missing {name} artifact URL in {route}: {expected}",
            errors,
        )

    malformed = tuple(
        f"/media-experiment-ledger{fragment}"
        for fragment in (
            *[f"{route}/" for route in PRIMARY_ROUTES],
            "data/",
        )
    )
    for route, html in pages.items():
        for fragment in malformed:
            require(fragment not in html, f"Malformed base path in {route}: {fragment}", errors)

    for name, relative_path, _, _ in DATA_ARTIFACTS:
        path = root / relative_path
        require(path.is_file(), f"Missing deployed artifact: {path}", errors)
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                require(isinstance(payload, dict), f"Artifact is not a JSON object: {path}", errors)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON in {path}: {exc}")

    files = [path for path in root.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    require(
        total_bytes <= MAX_SITE_BYTES,
        f"Pages artifact is unexpectedly large: {total_bytes:,} bytes > {MAX_SITE_BYTES:,}",
        errors,
    )
    for path in files:
        size = path.stat().st_size
        require(
            size <= MAX_FILE_BYTES,
            f"Pages artifact contains an unexpectedly large file: {path} ({size:,} bytes)",
            errors,
        )

    if errors:
        raise SystemExit("Site validation failed:\n- " + "\n- ".join(errors))
    print(
        f"Validated {len(PRIMARY_ROUTES)} routes, {len(DATA_ARTIFACTS)} data artifacts, "
        f"and {len(files)} files ({total_bytes:,} bytes) under {BASE}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    args = parser.parse_args()
    validate(args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
