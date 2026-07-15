import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("forecast_experiments", ROOT / "tools" / "forecast_experiments.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class ForecastTests(unittest.TestCase):
    def test_generates_bounded_forecasts_and_monthly_simulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            daily = []
            for index in range(12):
                daily.append(
                    {
                        "period": f"2026-07-{index + 1:02d}",
                        "runs": 1 + (index % 2),
                        "image_completed": 30 + index * 3,
                        "video_completed": 5 + (index % 3),
                        "errors": index % 2,
                        "success_rate": 0.97 - (index % 2) * 0.01,
                        "latency_mean_s": 70 - index * 0.8,
                    }
                )
            source = root / "data.json"
            source.write_text(json.dumps({"daily": daily}), encoding="utf-8")
            output = root / "forecasts"
            result = mod.generate(source, output)

            self.assertEqual(result["schema_version"], 1)
            self.assertGreaterEqual(result["confidence"]["score"], 5)
            self.assertLessEqual(result["confidence"]["score"], 95)
            success = result["next_active_day"]["targets"]["success_rate"]
            self.assertGreaterEqual(success["lower_80"], 0)
            self.assertLessEqual(success["upper_80"], 1)
            self.assertGreaterEqual(result["next_month"]["images"]["median"], 0)
            self.assertTrue((output / "forecast.json").exists())
            self.assertTrue((output / "report.md").exists())
            self.assertTrue((output / "model-card.md").exists())
            self.assertTrue((output / "history.jsonl").exists())

    def test_clean_rows_requires_four_dates(self):
        with self.assertRaises(ValueError):
            mod.clean_rows([{"period": "2026-07-01", "runs": 1}])


if __name__ == "__main__":
    unittest.main()
