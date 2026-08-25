# Forecast Lab

Generated: `2026-08-25T16:32:15+00:00`

Data fingerprint: `e2d086a253ed7cd4ad03314f4c443280de0f27e52a3ac92d061df22bf5f43fc2`

Confidence: **Strong (80/100)**

## Next active experiment day

Estimated date: **2026-08-27** 
(80% empirical window 2026-08-27 to 2026-08-30)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 1.0–1.0 |
| Images | 95.9 | 0.0–167.4 |
| Videos | 0.5 | 0.0–3.7 |
| Errors | 2.0 | 0.2–2.4 |
| Success rate | 96.5% | 88.8%–98.7% |
| Mean latency | 57.5 | 44.4–74.6 |

## Next calendar month — 2026-09

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 16 | 13–20 |
| Runs | 16 | 13–20 |
| Images | 1644 | 1175–2178 |
| Videos | 21 | 13–32 |
| Errors | 30 | 22–39 |
| Success | 98.2% | 97.7%–98.6% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
