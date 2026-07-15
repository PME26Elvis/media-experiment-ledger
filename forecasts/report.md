# Forecast Lab

Generated: `2026-07-15T03:05:16+00:00`

Data fingerprint: `5ed4c69f341caa54c851dc8346b4f79fef4a7e413eddcd2ee43f0410704bd12b`

Confidence: **Developing (49/100)**

## Next active experiment day

Estimated date: **2026-07-16** 
(80% empirical window 2026-07-16 to 2026-07-21)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.0 | 0.8–1.0 |
| Images | 26.6 | 0.0–113.0 |
| Videos | 2.8 | 0.0–7.2 |
| Errors | 1.8 | 0.2–3.4 |
| Success rate | 79.8% | 49.7%–93.3% |
| Mean latency | 75.1 | 62.5–119.4 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 16 | 11–21 |
| Images | 766 | 453–1133 |
| Videos | 60 | 38–86 |
| Errors | 31 | 21–43 |
| Success | 96.4% | 94.7%–97.4% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
