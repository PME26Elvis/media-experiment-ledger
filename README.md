# Agnes Media Harvester

Slow, single-key Agnes AI media harvester for text-to-video first, then text-to-image.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set AGNES_API_KEY
```

## Run

```bash
python agnes_media_harvester.py --config agnes_media_config.yaml
```

Dry run without calling APIs:

```bash
python agnes_media_harvester.py --dry-run --reset-state --run-stamp test
```

Run only video or only image:

```bash
python agnes_media_harvester.py --phase video
python agnes_media_harvester.py --phase image
```

## Prompt banks

- `prompts/video_prompts.jsonl`: 7 text-to-video prompts
- `prompts/image_prompts.jsonl`: 550 text-to-image prompts expected for the full run

Each line:

```json
{"id":"i0001","category":"product","prompt":"A professional product photo..."}
```

## Output layout

```text
results/YYYY-MM-DD/run_YYYYMMDD_HHMMSS/
  outputs.jsonl
  errors.jsonl
  media/
    images/
    videos/
logs/
state/
```

`state/agnes_media_state.json` tracks successful prompt ids per local date, so same-day reruns resume instead of repeating successes. Use `--reset-state` only when you intentionally want to rerun the same day.

## Conservative defaults

- Video: one create attempt every 360 seconds, `241` frames at `24` fps, approximately 10 seconds.
- Image: one create attempt every 90 seconds, `2048x2048`, URL output.
- Video phase stops before image phase if quota/rate-limit/server-busy errors occur.
- Image phase stops on quota/rate-limit/server-busy errors.

The point is slow free-tier observation, not maximum throughput.
