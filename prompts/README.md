# Prompt files

The harvester reads JSONL prompt banks.

Each line must be a JSON object:

```json
{"id":"i0001","category":"product","prompt":"A professional product photo..."}
```

Required fields:
- `id`: unique id, stable across runs
- `prompt`: text prompt

Optional fields:
- `category`
- `notes`

The script skips prompt ids that already succeeded today unless you reset state.
