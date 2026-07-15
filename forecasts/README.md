# Forecast artifacts

`tools/forecast_experiments.py` regenerates this directory after canonical analytics are updated.

- `forecast.json`: machine-readable predictions and model arena
- `report.md`: human-readable next-active-day and next-month summary
- `model-card.md`: target-specific cross-validation weights and MAE
- `history.jsonl`: one compact record per distinct analytics fingerprint
- `logs/latest.json`: latest forecast execution summary

The site consumes `forecast.json` after the workflow copies it to `web/public/data/forecast.json`.
