"""Monthly simulation, regime diagnostics, confidence, and forecast artifact writers."""
from __future__ import annotations

import hashlib
import json
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from forecast_model import SIMULATIONS, TARGETS

def simulate_month(
    rows: list[dict[str, Any]],
    forecasts: dict[str, dict[str, Any]],
    next_date_info: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, Any]:
    last_date = rows[-1]["date"]
    if last_date.month == 12:
        month_start = date(last_date.year + 1, 1, 1)
    else:
        month_start = date(last_date.year, last_date.month + 1, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)

    gaps = np.asarray(next_date_info["historical_gaps_days"], dtype=int)
    gap_weights = np.linspace(0.55, 1.0, len(gaps))
    gap_weights /= gap_weights.sum()

    totals = {name: np.zeros(SIMULATIONS, dtype=float) for name in ("runs", "image_completed", "video_completed", "errors")}
    active_days = np.zeros(SIMULATIONS, dtype=float)

    for simulation in range(SIMULATIONS):
        cursor = last_date
        dates_in_month = []
        guard = 0
        while cursor < month_end and guard < 366:
            gap = int(rng.choice(gaps, p=gap_weights))
            cursor += timedelta(days=max(1, gap))
            if month_start <= cursor < month_end:
                dates_in_month.append(cursor)
            guard += 1
        active_days[simulation] = len(dates_in_month)
        for target in totals:
            samples = forecasts[target]["samples"]
            if dates_in_month:
                chosen = rng.choice(samples, size=len(dates_in_month), replace=True)
                totals[target][simulation] = float(np.sum(chosen))

    successes = totals["image_completed"] + totals["video_completed"]
    attempts = successes + totals["errors"]
    success_rate = np.divide(successes, attempts, out=np.ones_like(successes), where=attempts > 0)

    def summary(samples: np.ndarray, integer: bool = False) -> dict[str, float]:
        lower, median, upper = np.quantile(samples, [0.1, 0.5, 0.9])
        if integer:
            return {"lower_80": int(round(lower)), "median": int(round(median)), "upper_80": int(round(upper))}
        return {"lower_80": float(lower), "median": float(median), "upper_80": float(upper)}

    return {
        "period": month_start.strftime("%Y-%m"),
        "method": "10,000-run Monte Carlo simulation using empirical active-day gaps and bootstrapped ensemble residuals",
        "active_days": summary(active_days, True),
        "runs": summary(totals["runs"], True),
        "images": summary(totals["image_completed"], True),
        "videos": summary(totals["video_completed"], True),
        "errors": summary(totals["errors"], True),
        "success_rate": summary(success_rate, False),
    }


def regime(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = np.asarray([row["image_completed"] + row["video_completed"] for row in rows], dtype=float)
    success = np.asarray([row["success_rate"] for row in rows if row["success_rate"] is not None], dtype=float)
    errors = np.asarray([row["errors"] for row in rows], dtype=float)
    recent = min(3, len(rows))
    earlier_outputs = outputs[:-recent] if len(outputs) > recent else outputs
    delta_outputs = float(np.mean(outputs[-recent:]) - np.mean(earlier_outputs))
    earlier_success = success[:-recent] if len(success) > recent else success
    delta_success = float(np.mean(success[-recent:]) - np.mean(earlier_success)) if len(success) else 0.0
    volatility = float(np.std(outputs) / max(1.0, np.mean(outputs)))
    recent_errors = float(np.mean(errors[-recent:]))
    earlier_errors = float(np.mean(errors[:-recent])) if len(errors) > recent else recent_errors

    if delta_success < -0.05 or recent_errors > earlier_errors + 1.0:
        label, tone = "Degrading", "risk"
    elif delta_success > 0.03 and recent_errors <= earlier_errors:
        label, tone = "Recovering", "positive"
    elif volatility > 0.85:
        label, tone = "Volatile", "warning"
    else:
        label, tone = "Stable", "neutral"
    return {
        "label": label,
        "tone": tone,
        "output_delta": delta_outputs,
        "success_delta": delta_success,
        "coefficient_of_variation": volatility,
        "recent_mean_errors": recent_errors,
    }


def confidence(rows: list[dict[str, Any]], forecasts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    sample_score = min(1.0, n / 24.0)
    folds = statistics.fmean([forecast["cv_folds"] for forecast in forecasts.values()])
    fold_score = min(1.0, folds / 8.0)
    normalized_errors = []
    for forecast in forecasts.values():
        top = forecast["models"][0]
        scale = max(1.0, abs(forecast["point"]))
        normalized_errors.append(min(1.0, top["mae"] / scale))
    accuracy_score = 1.0 - statistics.fmean(normalized_errors)
    score = round(100 * (0.45 * sample_score + 0.25 * fold_score + 0.30 * accuracy_score))
    score = max(5, min(95, score))
    if score < 35:
        label = "Experimental"
    elif score < 60:
        label = "Developing"
    elif score < 80:
        label = "Moderate"
    else:
        label = "Strong"
    return {
        "score": score,
        "label": label,
        "observed_dates": n,
        "mean_backtest_folds": round(folds, 1),
        "note": "Intervals describe model and residual uncertainty, not guaranteed future bounds.",
    }


def serialize_forecast(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"samples", "backtest_residuals"}}


def fingerprint(rows: list[dict[str, Any]]) -> str:
    normalized = [
        {key: (value.isoformat() if isinstance(value, date) else value) for key, value in row.items()}
        for row in rows
    ]
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def write_outputs(output_root: Path, result: dict[str, Any]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "forecast.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    target_rows = []
    for key, forecast in result["next_active_day"]["targets"].items():
        fmt = (lambda x: f"{x * 100:.1f}%") if forecast["kind"] == "rate" else (lambda x: f"{x:.1f}")
        target_rows.append(
            f"| {forecast['label']} | {fmt(forecast['point'])} | {fmt(forecast['lower_80'])}–{fmt(forecast['upper_80'])} |"
        )
    monthly = result["next_month"]
    report = [
        "# Forecast Lab", "",
        f"Generated: `{result['generated_at_utc']}`", "",
        f"Data fingerprint: `{result['data_fingerprint']}`", "",
        f"Confidence: **{result['confidence']['label']} ({result['confidence']['score']}/100)**", "",
        "## Next active experiment day", "",
        f"Estimated date: **{result['next_active_day']['date']['point_date']}** ",
        f"(80% empirical window {result['next_active_day']['date']['earliest_date']} to {result['next_active_day']['date']['latest_date']})", "",
        "| Target | Ensemble point | 80% interval |", "|---|---:|---:|", *target_rows, "",
        f"## Next calendar month — {monthly['period']}", "",
        "| Metric | Median | 80% interval |", "|---|---:|---:|",
        f"| Active days | {monthly['active_days']['median']} | {monthly['active_days']['lower_80']}–{monthly['active_days']['upper_80']} |",
        f"| Runs | {monthly['runs']['median']} | {monthly['runs']['lower_80']}–{monthly['runs']['upper_80']} |",
        f"| Images | {monthly['images']['median']} | {monthly['images']['lower_80']}–{monthly['images']['upper_80']} |",
        f"| Videos | {monthly['videos']['median']} | {monthly['videos']['lower_80']}–{monthly['videos']['upper_80']} |",
        f"| Errors | {monthly['errors']['median']} | {monthly['errors']['lower_80']}–{monthly['errors']['upper_80']} |",
        f"| Success | {monthly['success_rate']['median'] * 100:.1f}% | {monthly['success_rate']['lower_80'] * 100:.1f}%–{monthly['success_rate']['upper_80'] * 100:.1f}% |",
        "", "## Methodology", "",
        "Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.", "",
    ]
    (output_root / "report.md").write_text("\n".join(report), encoding="utf-8")

    model_lines = ["# Forecast model card", "", "## Model arena", ""]
    for target, models in result["model_arena"].items():
        model_lines += [f"### {TARGETS[target]['label']}", "", "| Model | Weight | MAE | Folds |", "|---|---:|---:|---:|"]
        model_lines += [f"| {row['model']} | {row['weight'] * 100:.1f}% | {row['mae']:.3f} | {row['folds']} |" for row in models]
        model_lines.append("")
    (output_root / "model-card.md").write_text("\n".join(model_lines), encoding="utf-8")

    log = {
        "generated_at_utc": result["generated_at_utc"],
        "data_fingerprint": result["data_fingerprint"],
        "confidence": result["confidence"],
        "regime": result["regime"],
        "next_active_date": result["next_active_day"]["date"],
        "target_points": {key: value["point"] for key, value in result["next_active_day"]["targets"].items()},
    }
    logs = output_root / "logs"
    logs.mkdir(exist_ok=True)
    (logs / "latest.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history_path = output_root / "history.jsonl"
    existing = history_path.read_text(encoding="utf-8").splitlines() if history_path.exists() else []
    if not existing or json.loads(existing[-1]).get("data_fingerprint") != result["data_fingerprint"]:
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log, ensure_ascii=False, separators=(",", ":")) + "\n")
