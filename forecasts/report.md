# Forecast Lab

Generated: `2026-08-04T04:39:19+00:00`

Data fingerprint: `1366730e04e13e19afefe0579aa18147c58809bd7f4ff54eb7bbde6bed698d85`

Confidence: **Moderate (73/100)**

## Next active experiment day

Estimated date: **2026-08-05** 
(80% empirical window 2026-08-05 to 2026-08-08)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 0.9–1.1 |
| Images | 30.7 | 0.0–335.3 |
| Videos | 6.0 | 6.4–8.7 |
| Errors | 1.2 | 0.4–1.3 |
| Success rate | 85.4% | 81.8%–100.0% |
| Mean latency | 84.9 | 20.3–149.1 |

## Next calendar month — 2026-09

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 16 | 12–20 |
| Runs | 16 | 12–20 |
| Images | 1389 | 698–2228 |
| Videos | 120 | 92–151 |
| Errors | 16 | 12–20 |
| Success | 99.0% | 98.2%–99.3% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
