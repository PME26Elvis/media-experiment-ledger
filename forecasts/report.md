# Forecast Lab

Generated: `2026-07-20T05:15:51+00:00`

Data fingerprint: `5ed4c69f341caa54c851dc8346b4f79fef4a7e413eddcd2ee43f0410704bd12b`

Confidence: **Developing (49/100)**

## Next active experiment day

Estimated date: **2026-07-21** 
(80% empirical window 2026-07-21 to 2026-07-26)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 0.9–1.1 |
| Images | 26.8 | 0.0–113.2 |
| Videos | 2.2 | 0.0–6.6 |
| Errors | 2.0 | 0.5–3.6 |
| Success rate | 73.5% | 43.5%–87.1% |
| Mean latency | 83.8 | 71.4–128.1 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 17 | 12–22 |
| Images | 768 | 459–1127 |
| Videos | 55 | 34–79 |
| Errors | 35 | 24–48 |
| Success | 96.0% | 94.1%–97.1% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
