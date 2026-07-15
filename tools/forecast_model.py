#!/usr/bin/env python3
"""Forecast future active experiment days and monthly output scenarios.

The forecaster is intentionally conservative for small datasets. It builds a
multi-model ensemble, evaluates candidates with rolling-origin backtests,
constructs empirical prediction intervals from out-of-sample residuals, and
runs Monte Carlo simulations for the next calendar month.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
from sklearn.base import RegressorMixin
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RNG_SEED = 42
SIMULATIONS = 10_000
TARGETS = {
    "runs": {"label": "Runs", "kind": "count"},
    "image_completed": {"label": "Images", "kind": "count"},
    "video_completed": {"label": "Videos", "kind": "count"},
    "errors": {"label": "Errors", "kind": "count"},
    "success_rate": {"label": "Success rate", "kind": "rate"},
    "latency_mean_s": {"label": "Mean latency", "kind": "positive"},
}


@dataclass(frozen=True)
class Candidate:
    name: str
    factory: Callable[[], RegressorMixin] | None
    baseline: str | None = None


CANDIDATES = (
    Candidate("Last value", None, "last"),
    Candidate("Rolling median", None, "median"),
    Candidate("Damped drift", None, "drift"),
    Candidate("Ridge", lambda: make_pipeline(StandardScaler(), Ridge(alpha=2.0))),
    Candidate("Huber", lambda: make_pipeline(StandardScaler(), HuberRegressor(epsilon=1.35, alpha=0.01, max_iter=500))),
    Candidate(
        "Random forest",
        lambda: RandomForestRegressor(
            n_estimators=96,
            max_depth=4,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=RNG_SEED,
            n_jobs=-1,
        ),
    ),
    Candidate(
        "Extra trees",
        lambda: ExtraTreesRegressor(
            n_estimators=96,
            max_depth=5,
            min_samples_leaf=2,
            max_features=0.9,
            random_state=RNG_SEED,
            n_jobs=-1,
        ),
    ),
    Candidate(
        "Gradient boost",
        lambda: GradientBoostingRegressor(
            loss="huber",
            n_estimators=96,
            learning_rate=0.035,
            max_depth=2,
            min_samples_leaf=2,
            random_state=RNG_SEED,
        ),
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def daily_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("daily")
    if isinstance(rows, list) and rows:
        return sorted((dict(row) for row in rows), key=lambda row: str(row.get("period")))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in payload.get("runs", []):
        grouped.setdefault(str(run.get("date")), []).append(run)
    output: list[dict[str, Any]] = []
    for period, runs in sorted(grouped.items()):
        images = sum(int(run.get("image_completed") or 0) for run in runs)
        videos = sum(int(run.get("video_completed") or 0) for run in runs)
        errors = sum(int(run.get("errors") or 0) for run in runs)
        attempts = images + videos + errors
        latencies = [float(run["latency_mean_s"]) for run in runs if run.get("latency_mean_s") is not None]
        output.append(
            {
                "period": period,
                "runs": len(runs),
                "image_completed": images,
                "video_completed": videos,
                "errors": errors,
                "success_rate": (images + videos) / attempts if attempts else None,
                "latency_mean_s": statistics.fmean(latencies) if latencies else None,
            }
        )
    return output


def clean_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        try:
            parsed = date.fromisoformat(str(row["period"]))
        except (KeyError, ValueError):
            continue
        item = {"period": parsed.isoformat(), "date": parsed}
        for target, metadata in TARGETS.items():
            raw = row.get(target)
            if raw is None:
                item[target] = None
                continue
            value = float(raw)
            if metadata["kind"] == "rate":
                value = min(1.0, max(0.0, value))
            else:
                value = max(0.0, value)
            item[target] = value
        cleaned.append(item)
    if len(cleaned) < 4:
        raise ValueError("At least four active experiment dates are required for forecasting")
    return sorted(cleaned, key=lambda row: row["date"])


def transform(values: np.ndarray, kind: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if kind == "rate":
        clipped = np.clip(values, 0.002, 0.998)
        return np.log(clipped / (1.0 - clipped))
    return np.log1p(np.maximum(values, 0.0))


def inverse(values: np.ndarray | float, kind: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if kind == "rate":
        arr = 1.0 / (1.0 + np.exp(-np.clip(arr, -20, 20)))
        return np.clip(arr, 0.0, 1.0)
    return np.maximum(0.0, np.expm1(np.clip(arr, -20, 20)))


def feature_vector(history: list[float], current_date: date, previous_date: date, index: int) -> list[float]:
    if not history:
        raise ValueError("Feature generation requires history")
    recent = history[-3:]
    lag1 = history[-1]
    lag2 = history[-2] if len(history) > 1 else lag1
    lag3 = history[-3] if len(history) > 2 else lag2
    rolling_mean = float(np.mean(recent))
    rolling_std = float(np.std(recent)) if len(recent) > 1 else 0.0
    weights = np.geomspace(0.35, 1.0, num=len(history))
    ewma = float(np.average(history, weights=weights))
    gap = max(1, (current_date - previous_date).days)
    weekday = current_date.weekday()
    month = current_date.month
    return [
        float(index),
        float(gap),
        math.sin(2 * math.pi * weekday / 7),
        math.cos(2 * math.pi * weekday / 7),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
        lag1,
        lag2,
        lag3,
        rolling_mean,
        rolling_std,
        ewma,
    ]


def build_supervised(values: list[float], dates: list[date]) -> tuple[np.ndarray, np.ndarray]:
    features: list[list[float]] = []
    targets: list[float] = []
    for index in range(1, len(values)):
        features.append(feature_vector(values[:index], dates[index], dates[index - 1], index))
        targets.append(values[index])
    return np.asarray(features, dtype=float), np.asarray(targets, dtype=float)


def baseline_predict(kind: str, history: list[float]) -> float:
    if kind == "last":
        return history[-1]
    if kind == "median":
        return float(np.median(history[-4:]))
    if kind == "drift":
        if len(history) < 2:
            return history[-1]
        drift = (history[-1] - history[0]) / max(1, len(history) - 1)
        return history[-1] + 0.55 * drift
    raise ValueError(kind)


def candidate_prediction(candidate: Candidate, x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> float:
    if candidate.baseline:
        return baseline_predict(candidate.baseline, y_train.tolist())
    if candidate.factory is None:
        raise AssertionError(candidate)
    model = candidate.factory()
    model.fit(x_train, y_train)
    return float(model.predict(x_test.reshape(1, -1))[0])


def rolling_backtest(values: list[float], dates: list[date], kind: str) -> dict[str, Any]:
    transformed = transform(np.asarray(values, dtype=float), kind).tolist()
    x_all, y_all = build_supervised(transformed, dates)
    first_test = max(3, len(values) - 5)
    records: dict[str, list[dict[str, float]]] = {candidate.name: [] for candidate in CANDIDATES}

    for original_index in range(first_test, len(values)):
        sample_index = original_index - 1
        x_train = x_all[:sample_index]
        y_train = y_all[:sample_index]
        x_test = x_all[sample_index]
        actual = values[original_index]
        if len(y_train) < 2:
            continue
        for candidate in CANDIDATES:
            try:
                pred_t = candidate_prediction(candidate, x_train, y_train, x_test)
                prediction = float(inverse(pred_t, kind))
                records[candidate.name].append(
                    {"index": original_index, "actual": actual, "prediction": prediction, "error": actual - prediction}
                )
            except Exception:
                continue

    arena = []
    for candidate in CANDIDATES:
        rows = records[candidate.name]
        if not rows:
            continue
        errors = [abs(row["error"]) for row in rows]
        scale = max(1e-6, float(np.median(np.abs(np.asarray(values) - np.median(values)))))
        mae = float(np.mean(errors))
        arena.append(
            {
                "model": candidate.name,
                "mae": mae,
                "normalized_mae": mae / max(scale, 1.0),
                "folds": len(rows),
                "records": rows,
            }
        )
    arena.sort(key=lambda row: row["mae"])
    if not arena:
        raise RuntimeError("No candidate model completed rolling-origin backtests")

    inverse_scores = np.asarray([1.0 / (row["normalized_mae"] + 0.15) for row in arena])
    inverse_scores = np.clip(inverse_scores, 0.05, np.percentile(inverse_scores, 90))
    weights = inverse_scores / inverse_scores.sum()
    for row, weight in zip(arena, weights, strict=True):
        row["weight"] = float(weight)
    return {"arena": arena, "transformed": transformed, "x_all": x_all, "y_all": y_all}


def next_date_distribution(dates: list[date], rng: np.random.Generator, draws: int = SIMULATIONS) -> dict[str, Any]:
    gaps = np.asarray([(b - a).days for a, b in zip(dates, dates[1:]) if (b - a).days > 0], dtype=int)
    if not len(gaps):
        gaps = np.asarray([1], dtype=int)
    recent_weights = np.linspace(0.55, 1.0, len(gaps))
    recent_weights /= recent_weights.sum()
    sampled = rng.choice(gaps, size=draws, replace=True, p=recent_weights)
    sampled = np.maximum(1, sampled)
    q10, median, q90 = np.quantile(sampled, [0.1, 0.5, 0.9])
    last = dates[-1]
    return {
        "point_date": (last + timedelta(days=int(round(median)))).isoformat(),
        "earliest_date": (last + timedelta(days=int(max(1, round(q10))))).isoformat(),
        "latest_date": (last + timedelta(days=int(max(1, round(q90))))).isoformat(),
        "median_gap_days": float(median),
        "historical_gaps_days": gaps.tolist(),
    }


def fit_target(rows: list[dict[str, Any]], target: str, future_date: date, rng: np.random.Generator) -> dict[str, Any]:
    metadata = TARGETS[target]
    filtered = [(row["date"], row[target]) for row in rows if row[target] is not None]
    dates = [item[0] for item in filtered]
    values = [float(item[1]) for item in filtered]
    if len(values) < 4:
        raise ValueError(f"Not enough non-null observations for {target}")

    result = rolling_backtest(values, dates, metadata["kind"])
    transformed: list[float] = result["transformed"]
    x_all: np.ndarray = result["x_all"]
    y_all: np.ndarray = result["y_all"]
    future_x = np.asarray(
        feature_vector(transformed, future_date, dates[-1], len(values)),
        dtype=float,
    )

    model_predictions = []
    for arena_row in result["arena"]:
        candidate = next(candidate for candidate in CANDIDATES if candidate.name == arena_row["model"])
        try:
            pred_t = candidate_prediction(candidate, x_all, y_all, future_x)
            prediction = float(inverse(pred_t, metadata["kind"]))
        except Exception:
            continue
        model_predictions.append(
            {
                "model": candidate.name,
                "prediction": prediction,
                "weight": float(arena_row["weight"]),
                "mae": float(arena_row["mae"]),
                "folds": int(arena_row["folds"]),
            }
        )
    if not model_predictions:
        raise RuntimeError(f"No final model could forecast {target}")
    total_weight = sum(item["weight"] for item in model_predictions)
    for item in model_predictions:
        item["weight"] /= total_weight
    point = sum(item["prediction"] * item["weight"] for item in model_predictions)

    residuals: list[float] = []
    by_index: dict[int, list[tuple[float, float]]] = {}
    for arena_row in result["arena"]:
        weight = float(arena_row["weight"])
        for record in arena_row["records"]:
            by_index.setdefault(int(record["index"]), []).append((float(record["prediction"]), weight))
    for index, predictions in by_index.items():
        weight_sum = sum(weight for _, weight in predictions)
        ensemble = sum(pred * weight for pred, weight in predictions) / weight_sum
        residuals.append(values[index] - ensemble)
    if not residuals:
        residuals = [0.0]

    boot = rng.choice(np.asarray(residuals), size=SIMULATIONS, replace=True)
    robust_scale = max(1e-9, 1.4826 * float(np.median(np.abs(np.asarray(residuals) - np.median(residuals)))))
    jitter = rng.normal(0.0, robust_scale * 0.15, size=SIMULATIONS)
    samples = point + boot + jitter
    if metadata["kind"] == "rate":
        samples = np.clip(samples, 0.0, 1.0)
    else:
        samples = np.maximum(samples, 0.0)
    lower, median, upper = np.quantile(samples, [0.1, 0.5, 0.9])

    return {
        "label": metadata["label"],
        "kind": metadata["kind"],
        "point": float(point),
        "median": float(median),
        "lower_80": float(lower),
        "upper_80": float(upper),
        "history": [{"date": d.isoformat(), "value": v} for d, v in zip(dates, values, strict=True)],
        "models": sorted(model_predictions, key=lambda item: item["weight"], reverse=True),
        "backtest_residuals": residuals,
        "cv_folds": max((item["folds"] for item in model_predictions), default=0),
        "samples": samples,
    }
