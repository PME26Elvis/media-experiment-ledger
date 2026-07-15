# Forecast Lab

Generated: `2026-07-15T02:22:47+00:00`

Data fingerprint: `5ed4c69f341caa54c851dc8346b4f79fef4a7e413eddcd2ee43f0410704bd12b`

Confidence: **Developing (49/100)**

## Next active experiment day

Estimated date: **2026-07-14** 
(80% empirical window 2026-07-14 to 2026-07-19)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 0.9–1.1 |
| Images | 26.1 | 0.0–112.5 |
| Videos | 2.3 | 0.0–6.8 |
| Errors | 1.7 | 0.2–3.3 |
| Success rate | 74.6% | 44.6%–88.2% |
| Mean latency | 81.4 | 68.8–125.8 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 17 | 12–22 |
| Images | 762 | 452–1120 |
| Videos | 56 | 35–81 |
| Errors | 30 | 20–42 |
| Success | 96.5% | 94.8%–97.5% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
