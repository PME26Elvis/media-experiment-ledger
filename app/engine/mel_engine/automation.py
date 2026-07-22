from __future__ import annotations

import hashlib
import json
import os
import random
import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from .common import emit, json_fingerprint, read_json, sha256, write_json


@dataclass(frozen=True)
class Prompt:
    id: str
    prompt: str
    category: str = 'uncategorized'

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.prompt.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ErrorDecision:
    category: str
    terminal: bool
    stop_run: bool
    retry_after_seconds: float | None
    reason: str


class ApiError(RuntimeError):
    def __init__(
        self,
        status_code: int | None,
        message: str,
        *,
        retry_after: str | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.payload = payload


class AutomationStopped(RuntimeError):
    pass


class RateLimiter:
    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = max(0.0, interval_seconds)
        self._next_allowed = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed - now)
            if delay:
                time.sleep(delay)
            self._next_allowed = time.monotonic() + self.interval_seconds


class CircuitBreaker:
    def __init__(self, max_consecutive: int, window: int, max_error_rate: float, minimum_samples: int) -> None:
        self.max_consecutive = max(1, max_consecutive)
        self.window = max(1, window)
        self.max_error_rate = min(1.0, max(0.0, max_error_rate))
        self.minimum_samples = max(1, minimum_samples)
        self._recent: list[bool] = []
        self._consecutive = 0
        self._lock = threading.Lock()

    def record(self, success: bool) -> None:
        with self._lock:
            self._recent.append(success)
            self._recent = self._recent[-self.window :]
            self._consecutive = 0 if success else self._consecutive + 1

    def reason(self) -> str | None:
        with self._lock:
            if self._consecutive >= self.max_consecutive:
                return f'circuit breaker opened after {self._consecutive} consecutive errors'
            if len(self._recent) >= self.minimum_samples:
                error_rate = 1.0 - (sum(1 for value in self._recent if value) / len(self._recent))
                if error_rate > self.max_error_rate:
                    return f'circuit breaker opened at rolling error rate {error_rate:.1%}'
            return None


def _safe_id(value: str, fallback: str) -> str:
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '-', value).strip('-._')[:96]
    return sanitized or fallback


def load_prompts(path: Path) -> list[Prompt]:
    if not path.is_file():
        raise ValueError('Prompt source must be a UTF-8 text or JSONL file.')
    prompts: list[Prompt] = []
    for line_number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith('{'):
            value = json.loads(stripped)
            if not isinstance(value, dict) or not str(value.get('prompt') or '').strip():
                raise ValueError(f'{path}:{line_number}: JSONL row requires a non-empty prompt.')
            prompt_text = str(value['prompt']).strip()
            prompt_id = _safe_id(str(value.get('id') or value.get('prompt_id') or ''), f'p{line_number:05d}')
            category = str(value.get('category') or 'uncategorized')
        else:
            prompt_text = stripped
            prompt_id = f'p{line_number:05d}'
            category = 'uncategorized'
        prompts.append(Prompt(prompt_id, prompt_text, category))
    if not prompts:
        raise ValueError('Prompt file must contain at least one non-empty prompt.')
    duplicate_ids = sorted({item.id for item in prompts if sum(1 for other in prompts if other.id == item.id) > 1})
    if duplicate_ids:
        raise ValueError(f'Duplicate prompt IDs: {", ".join(duplicate_ids)}')
    return prompts


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            current = now or datetime.now(timezone.utc)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (parsed - current).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def classify_error(error: Exception, request: dict[str, Any]) -> ErrorDecision:
    status = getattr(error, 'status_code', None)
    retry_after = parse_retry_after(getattr(error, 'retry_after', None))
    text = str(error).lower()
    if status in (401, 403):
        return ErrorDecision('auth_or_permission', True, True, retry_after, 'API key or permission was rejected')
    if status in (400, 404, 405, 413, 415, 422, 431):
        return ErrorDecision('bad_request_or_config', True, True, retry_after, 'provider rejected request configuration')
    if status == 402 or any(token in text for token in ('quota', 'balance', 'payment', 'insufficient')):
        return ErrorDecision('quota_or_payment', True, bool(request.get('stop_on_quota_or_payment', True)), retry_after, 'quota or payment exhausted')
    if status == 429 or any(token in text for token in ('rate limit', 'too many requests', 'rpm')):
        return ErrorDecision('rate_limit', False, bool(request.get('stop_on_rate_limit', False)), retry_after, 'provider rate limit')
    if status in (408, 409, 499):
        return ErrorDecision('transient_or_duplicate', False, False, retry_after, 'transient timeout or conflict')
    if status in (500, 502, 503, 504, 520, 522, 524):
        return ErrorDecision('server_busy', False, bool(request.get('stop_on_server_busy', False)), retry_after, 'provider or upstream server unavailable')
    if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
        return ErrorDecision('network_or_timeout', False, False, retry_after, 'network or timeout failure')
    return ErrorDecision('unknown_error', False, False, retry_after, 'unclassified provider failure')


def _request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(method, url, headers=headers, json=json_body, params=params)
    try:
        payload: Any = response.json()
    except ValueError:
        payload = {'text': response.text[:4000]}
    if response.status_code >= 400:
        raise ApiError(
            response.status_code,
            json.dumps(payload, ensure_ascii=False)[:4000],
            retry_after=response.headers.get('retry-after'),
            payload=payload,
        )
    return payload if isinstance(payload, dict) else {'data': payload}


def _append_jsonl(path: Path, value: dict[str, Any], lock: threading.Lock) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n'
    with lock:
        with path.open('a', encoding='utf-8') as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())


def _download_output(client: httpx.Client, url: str, destination: Path, max_bytes: int) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError(f'Provider output URL must use HTTPS: {url}')
    temporary = destination.with_suffix(destination.suffix + '.partial')
    digest = hashlib.sha256()
    size = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with client.stream('GET', url, follow_redirects=True) as response:
        response.raise_for_status()
        with temporary.open('wb') as stream:
            for chunk in response.iter_bytes(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f'Provider output exceeded configured maximum of {max_bytes} bytes.')
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    temporary.replace(destination)
    return {'path': str(destination), 'size_bytes': size, 'sha256': digest.hexdigest()}


def _image_url(payload: dict[str, Any]) -> str | None:
    rows = payload.get('data')
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return str(rows[0].get('url') or '') or None
    return str(payload.get('url') or '') or None


def _video_url(payload: dict[str, Any]) -> str | None:
    for key in ('video_url', 'url', 'remixed_from_video_id'):
        if payload.get(key):
            return str(payload[key])
    data = payload.get('data')
    if isinstance(data, dict):
        return _video_url(data)
    return None


def _poll_video(
    client: httpx.Client,
    *,
    base_url: str,
    headers: dict[str, str],
    model: str,
    video_id: str,
    task_id: str | None,
    poll_interval: float,
    poll_timeout: float,
    prompt_id: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + poll_timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            last = _request_json(
                client,
                'GET',
                f'{base_url}/agnesapi',
                headers=headers,
                params={'video_id': video_id, 'model_name': model},
            )
        except ApiError:
            if not task_id:
                raise
            last = _request_json(client, 'GET', f'{base_url}/v1/videos/{task_id}', headers=headers)
        status = str(last.get('status') or '').lower()
        emit('progress', stage='polling-video', prompt_id=prompt_id, provider_status=status, provider_progress=last.get('progress'))
        if status in {'completed', 'succeeded', 'success'} or _video_url(last):
            return last
        if status in {'failed', 'error', 'cancelled', 'canceled'}:
            raise ApiError(None, json.dumps(last, ensure_ascii=False), payload=last)
        time.sleep(max(1.0, poll_interval))
    raise ApiError(408, f'video polling timeout after {poll_timeout}s for {video_id}', payload=last)


def _sleep_backoff(attempt: int, decision: ErrorDecision, request: dict[str, Any]) -> None:
    base = max(1.0, float(request.get('retry_base_seconds', 15)))
    maximum = max(base, float(request.get('retry_max_seconds', 300)))
    delay = decision.retry_after_seconds
    if delay is None:
        delay = min(maximum, base * (2 ** max(0, attempt - 1)))
        delay *= random.uniform(0.85, 1.15)
    time.sleep(max(0.0, delay))


def run_automation(request: dict[str, Any]) -> dict[str, Any]:
    if str(request.get('provider', 'agnes')).lower() != 'agnes':
        raise ValueError('Only the Agnes provider adapter is enabled in the v1 registry.')
    api_key = os.environ.get(str(request.get('api_key_env') or 'AGNES_API_KEY'))
    if not api_key:
        raise ValueError('The selected credential profile did not provide the Agnes API key.')

    media_type = str(request.get('media_type', 'image')).lower()
    if media_type not in {'image', 'video'}:
        raise ValueError('media_type must be image or video.')
    prompts = load_prompts(Path(str(request.get('prompt_file') or '')).expanduser().resolve())
    output = Path(str(request.get('output_path') or '.')).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / 'automation-state.json'
    manifest_path = output / 'automation-manifest.json'
    events_path = output / 'automation-events.jsonl'
    media_root = output / 'media' / ('images' if media_type == 'image' else 'videos')

    base_url = str(request.get('base_url') or 'https://apihub.agnes-ai.com').rstrip('/')
    if urlparse(base_url).scheme != 'https':
        raise ValueError('Agnes base_url must use HTTPS.')
    model = str(request.get('model') or ('agnes-image-2.1-flash' if media_type == 'image' else 'agnes-video-v2.0'))
    config_identity = {
        'provider': 'agnes',
        'media_type': media_type,
        'model': model,
        'base_url': base_url,
        'prompts': [{'id': prompt.id, 'sha256': prompt.digest} for prompt in prompts],
    }
    fingerprint = json_fingerprint(config_identity)
    state = read_json(state_path, {})
    if not isinstance(state, dict) or state.get('fingerprint') != fingerprint:
        state = {
            'schema_version': 2,
            'fingerprint': fingerprint,
            'completed': {},
            'pending_videos': {},
            'attempts': {},
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        write_json(state_path, state)

    completed: dict[str, Any] = dict(state.get('completed') or {})
    pending_videos: dict[str, Any] = dict(state.get('pending_videos') or {})
    attempts: dict[str, int] = {str(key): int(value) for key, value in dict(state.get('attempts') or {}).items()}
    state_lock = threading.Lock()
    event_lock = threading.Lock()
    rate_limiter = RateLimiter(float(request.get('interval_seconds', 90)))
    breaker = CircuitBreaker(
        int(request.get('max_consecutive_errors', 3)),
        int(request.get('error_rate_window', 20)),
        float(request.get('max_error_rate', 0.5)),
        int(request.get('error_rate_minimum_samples', 6)),
    )
    max_attempts = max(1, int(request.get('max_attempts_per_prompt', 3)))
    max_requests = max(1, int(request.get('max_requests', len(prompts) * max_attempts + len(pending_videos) * 100)))
    max_failures = max(1, int(request.get('max_failures', max(3, len(prompts)))))
    max_wall_time = max(60.0, float(request.get('max_wall_time_seconds', 24 * 60 * 60)))
    max_output_bytes = max(1024, int(request.get('max_output_bytes', 2_000_000_000)))
    poll_interval = max(1.0, float(request.get('poll_interval_seconds', 30)))
    poll_timeout = max(poll_interval, float(request.get('poll_timeout_seconds', 2400)))
    started = time.monotonic()
    counters = {'requests': 0, 'failures': 0}
    counters_lock = threading.Lock()
    stop_event = threading.Event()
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    def persist() -> None:
        with state_lock:
            state['completed'] = completed
            state['pending_videos'] = pending_videos
            state['attempts'] = attempts
            state['updated_at'] = datetime.now(timezone.utc).isoformat()
            write_json(state_path, state)
            manifest = {
                'schema_version': 2,
                **config_identity,
                'fingerprint': fingerprint,
                'prompt_count': len(prompts),
                'completed_count': len(completed),
                'pending_video_count': len(pending_videos),
                'completed': completed,
                'pending_videos': pending_videos,
                'limits': {
                    'max_requests': max_requests,
                    'max_failures': max_failures,
                    'max_wall_time_seconds': max_wall_time,
                },
                'updated_at': state['updated_at'],
            }
            write_json(manifest_path, manifest)

    def budget_check() -> None:
        reason = breaker.reason()
        if reason:
            stop_event.set()
            raise AutomationStopped(reason)
        if time.monotonic() - started > max_wall_time:
            stop_event.set()
            raise AutomationStopped('maximum automation wall time reached')
        with counters_lock:
            if counters['requests'] >= max_requests:
                stop_event.set()
                raise AutomationStopped('maximum provider request budget reached')
            if counters['failures'] >= max_failures:
                stop_event.set()
                raise AutomationStopped('maximum failure budget reached')

    def provider_request(
        client: httpx.Client,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        paced: bool = False,
    ) -> dict[str, Any]:
        budget_check()
        if paced:
            rate_limiter.wait()
        with counters_lock:
            counters['requests'] += 1
        return _request_json(client, method, url, headers=headers, json_body=json_body, params=params)

    def process(prompt: Prompt) -> dict[str, Any]:
        if prompt.id in completed:
            return completed[prompt.id]
        event_base = {
            'prompt_id': prompt.id,
            'prompt_sha256': prompt.digest,
            'prompt_length': len(prompt.prompt),
            'category': prompt.category,
            'media_type': media_type,
            'model': model,
        }
        timeout = httpx.Timeout(connect=30, read=900, write=120, pool=30)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            for attempt in range(attempts.get(prompt.id, 0) + 1, max_attempts + 1):
                if stop_event.is_set():
                    raise AutomationStopped('automation was stopped by another worker')
                attempts[prompt.id] = attempt
                persist()
                try:
                    pending = pending_videos.get(prompt.id)
                    if media_type == 'video' and pending:
                        result = _poll_video(
                            client,
                            base_url=base_url,
                            headers=headers,
                            model=model,
                            video_id=str(pending['video_id']),
                            task_id=str(pending.get('task_id') or '') or None,
                            poll_interval=poll_interval,
                            poll_timeout=poll_timeout,
                            prompt_id=prompt.id,
                        )
                    else:
                        payload: dict[str, Any] = {'prompt': prompt.prompt, 'model': model}
                        if media_type == 'video':
                            payload.update({
                                'num_frames': int(request.get('num_frames', 241)),
                                'frame_rate': int(request.get('frame_rate', 24)),
                                'seed': int(request.get('seed', random.randint(1, 2_147_483_647))),
                            })
                            if request.get('width') is not None:
                                payload['width'] = int(request['width'])
                            if request.get('height') is not None:
                                payload['height'] = int(request['height'])
                            if request.get('negative_prompt'):
                                payload['negative_prompt'] = str(request['negative_prompt'])
                        result = provider_request(
                            client,
                            'POST',
                            f'{base_url}/v1/images/generations' if media_type == 'image' else f'{base_url}/v1/videos',
                            json_body=payload,
                            paced=True,
                        )
                        if media_type == 'video':
                            video_id = str(result.get('video_id') or result.get('id') or result.get('task_id') or '')
                            task_id = str(result.get('task_id') or result.get('id') or '') or None
                            if not video_id:
                                raise ApiError(None, 'Agnes video submission returned no video/task identifier.', payload=result)
                            pending_videos[prompt.id] = {'video_id': video_id, 'task_id': task_id, 'submitted_at': datetime.now(timezone.utc).isoformat()}
                            persist()
                            _append_jsonl(events_path, {**event_base, 'event': 'video_submitted', **pending_videos[prompt.id]}, event_lock)
                            result = _poll_video(
                                client,
                                base_url=base_url,
                                headers=headers,
                                model=model,
                                video_id=video_id,
                                task_id=task_id,
                                poll_interval=poll_interval,
                                poll_timeout=poll_timeout,
                                prompt_id=prompt.id,
                            )

                    url = _image_url(result) if media_type == 'image' else _video_url(result)
                    local: dict[str, Any] | None = None
                    if url and bool(request.get('download_outputs', True)):
                        suffix = '.png' if media_type == 'image' else '.mp4'
                        local = _download_output(client, url, media_root / f'{prompt.id}{suffix}', max_output_bytes)
                    record = {
                        **event_base,
                        'status': 'completed',
                        'attempt': attempt,
                        'output_url': url,
                        'local': local,
                        'provider_status': result.get('status'),
                        'completed_at': datetime.now(timezone.utc).isoformat(),
                    }
                    with state_lock:
                        completed[prompt.id] = record
                        pending_videos.pop(prompt.id, None)
                    breaker.record(True)
                    persist()
                    _append_jsonl(events_path, {**record, 'event': f'{media_type}_completed'}, event_lock)
                    return record
                except AutomationStopped:
                    raise
                except Exception as error:
                    decision = classify_error(error, request)
                    breaker.record(False)
                    with counters_lock:
                        counters['failures'] += 1
                    _append_jsonl(
                        events_path,
                        {
                            **event_base,
                            'event': f'{media_type}_error',
                            'attempt': attempt,
                            'error_class': decision.category,
                            'reason': decision.reason,
                            'http_status': getattr(error, 'status_code', None),
                            'retry_after_seconds': decision.retry_after_seconds,
                            'terminal': decision.terminal,
                            'stop_run': decision.stop_run,
                            'error': f'{type(error).__name__}: {error}',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                        },
                        event_lock,
                    )
                    persist()
                    if decision.stop_run or decision.terminal or attempt >= max_attempts:
                        if decision.stop_run:
                            stop_event.set()
                        raise
                    _sleep_backoff(attempt, decision, request)
        raise RuntimeError('unreachable automation worker state')

    remaining = [prompt for prompt in prompts if prompt.id not in completed]
    failures: list[dict[str, Any]] = []
    concurrency = min(8, max(1, int(request.get('concurrency', 1))))
    futures: dict[Future[dict[str, Any]], Prompt] = {}
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix='agnes') as executor:
        for prompt in remaining:
            futures[executor.submit(process, prompt)] = prompt
        for future in as_completed(futures):
            prompt = futures[future]
            try:
                future.result()
            except Exception as error:
                failures.append({'prompt_id': prompt.id, 'error': f'{type(error).__name__}: {error}'})
                if stop_event.is_set():
                    for pending in futures:
                        pending.cancel()
            completed_count = len(completed)
            emit(
                'progress',
                stage='automation',
                progress=completed_count / max(len(prompts), 1) * 100,
                completed=completed_count,
                total=len(prompts),
                failures=len(failures),
            )

    persist()
    result = read_json(manifest_path, {})
    result['failures'] = failures
    result['request_count'] = counters['requests']
    result['failure_count'] = counters['failures']
    result['effective_concurrency'] = concurrency
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    result['status'] = 'completed' if not failures else 'completed_with_errors'
    write_json(manifest_path, result)
    if failures and bool(request.get('fail_job_on_any_error', False)):
        raise RuntimeError(f'{len(failures)} automation prompt(s) failed; see {events_path}')
    return result
