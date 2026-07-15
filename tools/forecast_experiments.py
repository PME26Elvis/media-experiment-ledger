#!/usr/bin/env python3
"""Generate ensemble and Monte Carlo forecasts from canonical analytics."""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from forecast_model import CANDIDATES, RNG_SEED, TARGETS, clean_rows, daily_rows, fit_target, load_json, next_date_distribution
from forecast_report import confidence, fingerprint, regime, serialize_forecast, simulate_month, write_outputs

TAIPEI = ZoneInfo("Asia/Taipei")


def anchor_date_forecast(raw: dict[str, Any], last_observed: date, as_of_date: date) -> dict[str, Any]:
    """Move an inter-arrival forecast beyond the current as-of date.

    The empirical gap distribution is still learned from active experiment days,
    but a stale final observation must never produce a forecast in the past.
    """
    anchor = max(last_observed, as_of_date)

    def historical_gap(key: str) -> int:
        predicted = date.fromisoformat(str(raw[key]))
        return max(1, (predicted - last_observed).days)

    earliest_gap = historical_gap("earliest_date")
    point_gap = historical_gap("point_date")
    latest_gap = max(point_gap, historical_gap("latest_date"))
    return {
        **raw,
        "as_of_date_taipei": as_of_date.isoformat(),
        "anchor_date": anchor.isoformat(),
        "point_date": (anchor + timedelta(days=point_gap)).isoformat(),
        "earliest_date": (anchor + timedelta(days=earliest_gap)).isoformat(),
        "latest_date": (anchor + timedelta(days=latest_gap)).isoformat(),
    }


def generate(input_path: Path, output_root: Path, as_of_date: date | None = None) -> dict[str, Any]:
    payload = load_json(input_path)
    rows = clean_rows(daily_rows(payload))
    resolved_as_of = as_of_date or datetime.now(TAIPEI).date()
    rng = np.random.default_rng(RNG_SEED)
    raw_date_forecast = next_date_distribution([row["date"] for row in rows], rng)
    date_forecast = anchor_date_forecast(raw_date_forecast, rows[-1]["date"], resolved_as_of)
    future_date = date.fromisoformat(date_forecast["point_date"])

    raw_forecasts: dict[str, dict[str, Any]] = {}
    for target in TARGETS:
        try:
            raw_forecasts[target] = fit_target(rows, target, future_date, rng)
        except ValueError:
            continue
    required = {"runs", "image_completed", "video_completed", "errors"}
    if not required.issubset(raw_forecasts):
        missing = ", ".join(sorted(required - raw_forecasts.keys()))
        raise ValueError(f"Missing required target forecasts: {missing}")

    # simulate_month only consumes the final row date. Re-anchor it without
    # fabricating a new observed data point or changing the model history.
    monthly_rows = [dict(row) for row in rows]
    monthly_rows[-1] = {**monthly_rows[-1], "date": max(rows[-1]["date"], resolved_as_of)}
    monthly = simulate_month(monthly_rows, raw_forecasts, date_forecast, rng)
    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "as_of_date_taipei": resolved_as_of.isoformat(),
        "data_fingerprint": fingerprint(rows),
        "method": {
            "ensemble": "Inverse-error weighted ensemble after rolling-origin backtesting",
            "candidate_models": [candidate.name for candidate in CANDIDATES],
            "intervals": "80% empirical residual-bootstrap intervals",
            "monthly": "10,000 Monte Carlo simulations",
            "random_seed": RNG_SEED,
        },
        "confidence": confidence(rows, raw_forecasts),
        "regime": regime(rows),
        "next_active_day": {
            "date": date_forecast,
            "targets": {key: serialize_forecast(value) for key, value in raw_forecasts.items()},
        },
        "next_month": monthly,
        "model_arena": {key: value["models"] for key, value in raw_forecasts.items()},
        "observations": [
            {key: (value.isoformat() if isinstance(value, date) else value) for key, value in row.items()}
            for row in rows
        ],
    }
    write_outputs(output_root, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ensemble and Monte Carlo forecasts from analytics data")
    parser.add_argument("--input", type=Path, default=Path("site/data.json"))
    parser.add_argument("--output", type=Path, default=Path("forecasts"))
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        help="Taipei as-of date for reproducible backfills (YYYY-MM-DD); defaults to today in Asia/Taipei",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = generate(args.input, args.output, args.as_of_date)
        print(
            f"Forecasted {len(result['observations'])} active dates as of {result['as_of_date_taipei']}; "
            f"confidence={result['confidence']['label']} ({result['confidence']['score']}/100)"
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
