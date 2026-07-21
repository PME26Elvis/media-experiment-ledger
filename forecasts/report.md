# Forecast Lab

Generated: `2026-07-21T04:06:11+00:00`

Data fingerprint: `9bdb26aaa3e431b0a5492bce8cea633acf9edd8098b32ea6181fca36e0423bae`

Confidence: **Developing (49/100)**

## Next active experiment day

Estimated date: **2026-07-22** 
(80% empirical window 2026-07-22 to 2026-07-27)

| Target | Ensemble point | 80% interval |
|---|---:|---:|
| Runs | 1.1 | 0.9–1.1 |
| Images | 17.7 | 0.0–110.5 |
| Videos | 1.8 | 0.0–5.6 |
| Errors | 2.5 | 0.9–4.1 |
| Success rate | 67.1% | 37.0%–80.6% |
| Mean latency | 79.9 | 66.6–124.9 |

## Next calendar month — 2026-08

| Metric | Median | 80% interval |
|---|---:|---:|
| Active days | 17 | 12–22 |
| Runs | 17 | 12–22 |
| Images | 703 | 402–1049 |
| Videos | 49 | 31–70 |
| Errors | 43 | 29–57 |
| Success | 94.7% | 92.2%–96.1% |

## Methodology

Rolling-origin backtests select and weight robust baselines, regularized linear models, robust regression, random forests, extra trees, and gradient boosting. Prediction intervals use out-of-sample residual bootstrapping. Monthly totals use 10,000 Monte Carlo paths with empirical inter-arrival gaps.
