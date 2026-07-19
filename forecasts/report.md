# Forecast Lab

Generated: `2026-07-19T14:45:27+00:00`

Data fingerprint: `5ed4c69f341caa54c851dc8346b4f79fef4a7e413eddcd2ee43f0410704bd12b`

Confidence: **Developing (48/100)**

## Next active experiment day

Estimated date: **2026-07-20** 
(80% empirical window 2026-07-20 to 2026-07-25)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 0.9–1.1 |
| Images | 28.9 | 0.0–115.2 |
| Videos | 2.6 | 0.0–7.1 |
| Errors | 1.4 | 0.0–3.0 |
| Success rate | 86.0% | 55.9%–99.5% |
| Mean latency | 82.9 | 70.3–127.2 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 16 | 12–22 |
| Images | 783 | 467–1156 |
| Videos | 59 | 37–85 |
| Errors | 26 | 17–36 |
| Success | 97.0% | 95.6%–97.9% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
