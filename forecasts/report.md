# Forecast Lab

Generated: `2026-07-20T08:43:39+00:00`

Data fingerprint: `9bdb26aaa3e431b0a5492bce8cea633acf9edd8098b32ea6181fca36e0423bae`

Confidence: **Developing (49/100)**

## Next active experiment day

Estimated date: **2026-07-21** 
(80% empirical window 2026-07-21 to 2026-07-26)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.1 | 0.9–1.2 |
| Images | 18.0 | 0.0–110.8 |
| Videos | 2.0 | 0.0–5.8 |
| Errors | 2.0 | 0.5–3.6 |
| Success rate | 73.5% | 43.5%–87.1% |
| Mean latency | 86.7 | 73.5–131.8 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 17 | 12–23 |
| Images | 708 | 407–1051 |
| Videos | 51 | 32–72 |
| Errors | 35 | 24–48 |
| Success | 95.6% | 93.6%–96.9% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
