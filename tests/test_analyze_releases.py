import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("analyze_releases", Path(__file__).parents[1] / "tools" / "analyze_releases.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class AnalyzeReleaseTests(unittest.TestCase):
    def test_summarize_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "run_20260629_120000"
            (root / f"{run_id}-outputs.jsonl").write_text(
                json.dumps({"event": "image_completed", "timestamp": "2026-06-29T12:00:00+08:00", "finished_at": "2026-06-29T12:00:05+08:00", "category": "product", "payload": {"model": "m1"}}) + "\n"
                + json.dumps({"event": "video_completed", "timestamp": "2026-06-29T12:01:00+08:00", "finished_at": "2026-06-29T12:01:10+08:00", "category": "travel", "payload": {"model": "m2"}}) + "\n",
                encoding="utf-8",
            )
            (root / f"{run_id}-errors.jsonl").write_text(
                json.dumps({"event": "video_error", "error_class": "server_busy", "timestamp": "2026-06-29T12:02:00+08:00", "finished_at": "2026-06-29T12:02:03+08:00"}) + "\n",
                encoding="utf-8",
            )
            summary, errors = mod.summarize("2026-06-29", "media-exp-2026-06-29", {"run_id": run_id, "digest": "abc", "stats": {}}, root)
            self.assertEqual(summary["image_completed"], 1)
            self.assertEqual(summary["video_completed"], 1)
            self.assertEqual(summary["errors"], 1)
            self.assertAlmostEqual(summary["success_rate"], 2 / 3)
            self.assertEqual(summary["categories"]["product"], 1)
            self.assertEqual(errors[0]["error_class"], "server_busy")

    def test_aggregate_runs(self):
        rows = [
            {"date": "2026-06-29", "image_completed": 2, "video_completed": 1, "errors": 1, "latency_mean_s": 5.0, "source_bytes": 10},
            {"date": "2026-06-29", "image_completed": 3, "video_completed": 0, "errors": 0, "latency_mean_s": 7.0, "source_bytes": 20},
        ]
        daily = mod.aggregate(rows)
        self.assertEqual(daily[0]["runs"], 2)
        self.assertEqual(daily[0]["image_completed"], 5)
        self.assertEqual(daily[0]["video_completed"], 1)


if __name__ == "__main__":
    unittest.main()
