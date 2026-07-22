from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

from .common import emit, write_json


def run_automation(request: dict[str, Any]) -> dict[str, Any]:
    if str(request.get('provider', 'agnes')).lower() != 'agnes':
        raise ValueError('Only the Agnes provider adapter is enabled in the initial registry.')
    api_key = os.environ.get('AGNES_API_KEY')
    if not api_key:
        raise ValueError('AGNES_API_KEY is not available to the engine process.')
    media_type = str(request.get('media_type', 'image'))
    prompt_source = Path(str(request.get('prompt_file') or ''))
    output = Path(str(request.get('output_path') or '.')).resolve()
    output.mkdir(parents=True, exist_ok=True)
    prompts = [line.strip() for line in prompt_source.read_text(encoding='utf-8').splitlines() if line.strip()] if prompt_source.is_file() else []
    if not prompts:
        raise ValueError('Prompt file must contain at least one non-empty line.')
    endpoint = 'https://apihub.agnes-ai.com/v1/images/generations' if media_type == 'image' else 'https://apihub.agnes-ai.com/v1/videos'
    interval = max(0.0, float(request.get('interval_seconds', 90)))
    max_errors = max(1, int(request.get('max_consecutive_errors', 3)))
    events = []
    consecutive_errors = 0
    for index, prompt in enumerate(prompts, 1):
        body = {'prompt': prompt, 'model': request.get('model') or ('agnes-image-2.1-flash' if media_type == 'image' else 'agnes-video-v2.0')}
        http_request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(http_request, timeout=900) as response:
                payload = json.loads(response.read().decode())
            events.append({'prompt_index': index, 'status': 'submitted', 'response': payload})
            consecutive_errors = 0
        except Exception as error:
            consecutive_errors += 1
            events.append({'prompt_index': index, 'status': 'error', 'error': f'{type(error).__name__}: {error}'})
            write_json(output / 'automation-manifest.json', {'schema_version': 1, 'provider': 'agnes', 'media_type': media_type, 'events': events})
            if consecutive_errors >= max_errors:
                raise
        emit('progress', stage='submitting', progress=index / len(prompts) * 100, completed=index, total=len(prompts))
        if index < len(prompts):
            time.sleep(interval)
    manifest = {'schema_version': 1, 'provider': 'agnes', 'media_type': media_type, 'events': events}
    write_json(output / 'automation-manifest.json', manifest)
    return manifest
