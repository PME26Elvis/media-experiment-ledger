#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
import yaml
from dotenv import load_dotenv


DEFAULT_CONFIG = "agnes_media_config.yaml"


class ApiError(RuntimeError):
    def __init__(self, status_code: Optional[int], message: str, *, retry_after: Optional[str] = None, payload: Any = None):
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after
        self.payload = payload
        code = f"HTTP {status_code}" if status_code is not None else "ERROR"
        retry = f" retry_after={retry_after}" if retry_after else ""
        super().__init__(f"Agnes {code}{retry}: {message}")


class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, obj: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class Logger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
        print(line, flush=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


@dataclass
class PhaseDecision:
    error_class: str
    terminal: bool
    stop_phase: bool
    retry_after_seconds: Optional[int]
    reason: str


def now_tz(tz: ZoneInfo) -> datetime:
    return datetime.now(tz)


def today_str(tz: ZoneInfo) -> str:
    return now_tz(tz).date().isoformat()


def stamp(tz: ZoneInfo) -> str:
    return now_tz(tz).strftime("%Y%m%d_%H%M%S")


def sleep_interruptible(seconds: float, logger: Logger, reason: str) -> None:
    if seconds <= 0:
        return
    logger.log(f"[WAIT] {seconds:.1f}s {reason}")
    end = time.monotonic() + seconds
    while True:
        left = end - time.monotonic()
        if left <= 0:
            return
        time.sleep(min(30.0, left))


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Config YAML must be a mapping")
    return data


def load_prompts(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    with path.open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{n} must be a JSON object")
            pid = str(obj.get("id") or "").strip()
            prompt = str(obj.get("prompt") or "").strip()
            if not pid or not prompt:
                raise ValueError(f"{path}:{n} missing id/prompt")
            if pid in seen:
                raise ValueError(f"Duplicate prompt id in {path}: {pid}")
            seen.add(pid)
            rows.append(obj)
    if not rows:
        raise ValueError(f"No prompts loaded from {path}")
    return rows


def load_state(path: Path, today: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict) and state.get("date") == today:
                return state
        except Exception:
            broken = path.with_suffix(".broken.json")
            path.rename(broken)
    return {
        "date": today,
        "video": {"success_ids": [], "error_count": 0, "submitted": []},
        "image": {"success_ids": [], "error_count": 0},
    }


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def parse_retry_after(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return max(0, int(float(value)))
    except Exception:
        return None


def classify_error(exc: Exception, phase_cfg: Dict[str, Any]) -> PhaseDecision:
    status = getattr(exc, "status_code", None)
    retry_after = getattr(exc, "retry_after", None)
    retry_s = parse_retry_after(retry_after)
    text = str(exc)
    lower = text.lower()

    if status is None:
        m = re.search(r"\b(400|401|402|403|404|405|408|409|413|415|422|429|431|499|500|502|503|504|520|522|524)\b", text)
        if m:
            status = int(m.group(1))

    if status in (401, 403):
        return PhaseDecision("auth_or_permission", True, True, retry_s, "API key/permission issue")
    if status in (400, 404, 405, 413, 415, 422, 431):
        return PhaseDecision("bad_request_or_config", True, True, retry_s, "request/config issue")
    if status == 402 or "insufficient" in lower or "quota" in lower or "balance" in lower or "payment" in lower:
        return PhaseDecision("quota_or_payment", True, bool(phase_cfg.get("stop_on_quota_or_payment", True)), retry_s, "quota/payment exhausted")
    if status == 429 or "too many requests" in lower or "rate limit" in lower or "rpm" in lower:
        return PhaseDecision("rate_limit", False, bool(phase_cfg.get("stop_on_rate_limit", True)), retry_s, "rate/RPM limit")
    if status in (408, 409, 499):
        return PhaseDecision("transient_or_duplicate", False, False, retry_s, "transient timeout/conflict")
    if status in (500, 502, 503, 504, 520, 522, 524):
        return PhaseDecision("server_busy", False, bool(phase_cfg.get("stop_on_server_busy", True)), retry_s, "server busy/upstream timeout")
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
        return PhaseDecision("network_or_timeout", False, False, retry_s, "local/network timeout")
    return PhaseDecision("unknown_error", False, True, retry_s, "unknown error")


def request_json(client: httpx.Client, method: str, url: str, *, headers: Dict[str, str], json_body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = client.request(method, url, headers=headers, json=json_body, params=params)
    content_type = resp.headers.get("content-type", "")
    try:
        data = resp.json() if "json" in content_type or resp.text.strip().startswith(("{", "[")) else {"text": resp.text}
    except Exception:
        data = {"text": resp.text}
    if resp.status_code >= 400:
        raise ApiError(resp.status_code, json.dumps(data, ensure_ascii=False)[:4000], retry_after=resp.headers.get("retry-after"), payload=data)
    if not isinstance(data, dict):
        return {"data": data}
    return data


def choose_ext_from_response(url: str, resp: httpx.Response, default: str) -> str:
    ct = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    ext = mimetypes.guess_extension(ct) if ct else None
    if ext:
        return ext
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix
    return suffix or default


def download_url(client: httpx.Client, url: str, dest_without_ext: Path, default_ext: str) -> Optional[str]:
    if not url:
        return None
    resp = client.get(url, follow_redirects=True)
    resp.raise_for_status()
    ext = choose_ext_from_response(url, resp, default_ext)
    dest = dest_without_ext.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return str(dest)


def image_url_from_response(data: Dict[str, Any]) -> Optional[str]:
    arr = data.get("data") or []
    if isinstance(arr, list) and arr:
        first = arr[0] or {}
        return first.get("url")
    return None


def video_url_from_response(data: Dict[str, Any]) -> Optional[str]:
    return data.get("remixed_from_video_id") or data.get("video_url") or data.get("url")


def run_video_phase(client: httpx.Client, cfg: Dict[str, Any], state: Dict[str, Any], state_path: Path, run_dir: Path, writers: Dict[str, JsonlWriter], logger: Logger, tz: ZoneInfo, dry_run: bool) -> None:
    phase = "video"
    vcfg = cfg.get("video", {}) or {}
    if not vcfg.get("enabled", True):
        logger.log("[VIDEO] disabled")
        return
    prompts = load_prompts(Path(vcfg["prompt_file"]))
    success_ids = set(state.setdefault("video", {}).setdefault("success_ids", []))
    target_success = int(vcfg.get("target_success", len(prompts)))
    interval = float(vcfg.get("create_interval_seconds", 360))
    headers = {"Authorization": f"Bearer {os.environ.get(cfg['api_key_env'], 'DRY_RUN_KEY')}", "Content-Type": "application/json"}
    base_url = str(cfg.get("base_url", "https://apihub.agnes-ai.com")).rstrip("/")
    create_url = f"{base_url}/v1/videos"
    media_dir = run_dir / "media" / "videos"

    logger.log(f"[VIDEO] start target_success={target_success} already_success={len(success_ids)} prompts={len(prompts)} interval={interval}s")

    consecutive_errors = 0
    for prompt_obj in prompts:
        if len(success_ids) >= target_success:
            logger.log(f"[VIDEO] complete target_success={target_success}")
            return
        pid = str(prompt_obj["id"])
        if pid in success_ids:
            continue

        seed = random.randint(int(vcfg.get("seed_min", 1)), int(vcfg.get("seed_max", 2_147_483_647)))
        payload: Dict[str, Any] = {
            "model": str(vcfg.get("model", "agnes-video-v2.0")),
            "prompt": str(prompt_obj["prompt"]),
            "num_frames": int(vcfg.get("num_frames", 241)),
            "frame_rate": int(vcfg.get("frame_rate", 24)),
            "seed": seed,
        }
        if vcfg.get("width") is not None:
            payload["width"] = int(vcfg["width"])
        if vcfg.get("height") is not None:
            payload["height"] = int(vcfg["height"])
        if vcfg.get("negative_prompt"):
            payload["negative_prompt"] = str(vcfg["negative_prompt"])

        started = now_tz(tz).isoformat(timespec="seconds")
        record: Dict[str, Any] = {"phase": phase, "prompt_id": pid, "category": prompt_obj.get("category"), "timestamp": started, "payload": payload, "seed": seed}
        try:
            if dry_run:
                data = {"dry_run": True, "video_id": f"dry_{pid}", "status": "completed", "seconds": str(round(payload["num_frames"] / payload["frame_rate"], 2))}
            else:
                data = request_json(client, "POST", create_url, headers=headers, json_body=payload)
            record["create_response"] = data
            video_id = data.get("video_id") or data.get("id") or data.get("task_id")
            task_id = data.get("task_id") or data.get("id")
            record["video_id"] = video_id
            record["task_id"] = task_id
            writers["outputs"].write({**record, "event": "video_submitted"})
            logger.log(f"[VIDEO] submitted id={pid} video_id={video_id} seed={seed}")

            result = data
            if not dry_run and video_id:
                result = poll_video_result(client, cfg, vcfg, headers, video_id, task_id, logger)
            url = video_url_from_response(result)
            local_path = None
            if url and bool(vcfg.get("download_outputs", cfg.get("download_outputs", True))):
                try:
                    local_path = download_url(client, url, media_dir / f"{pid}_{video_id or task_id}", ".mp4")
                except Exception as dl_exc:
                    logger.log(f"[VIDEO] download failed id={pid}: {dl_exc}")

            success_ids.add(pid)
            state["video"]["success_ids"] = sorted(success_ids)
            save_state(state_path, state)
            writers["outputs"].write({**record, "event": "video_completed", "result": result, "output_url": url, "local_path": local_path, "finished_at": now_tz(tz).isoformat(timespec="seconds")})
            logger.log(f"[VIDEO] OK id={pid} success={len(success_ids)}/{target_success} url={url}")
            consecutive_errors = 0
            
            if not dry_run:
                sleep_interruptible(interval, logger, "next video create interval")
        except Exception as exc:
            decision = classify_error(exc, vcfg)
            consecutive_errors += 1
            err_record = {**record, "event": "video_error", "error": str(exc), "error_class": decision.error_class, "http_status": getattr(exc, "status_code", None), "retry_after": getattr(exc, "retry_after", None), "decision": decision.__dict__, "finished_at": now_tz(tz).isoformat(timespec="seconds")}
            writers["errors"].write(err_record)
            logger.log(f"[VIDEO] ERR id={pid} class={decision.error_class} stop={decision.stop_phase} terminal={decision.terminal} {str(exc)[:240]}")
            state["video"]["error_count"] = int(state["video"].get("error_count", 0)) + 1
            save_state(state_path, state)
            if decision.stop_phase or consecutive_errors >= int(vcfg.get("max_consecutive_errors", 1)):
                logger.log(f"[VIDEO] stop phase reason={decision.reason} consecutive_errors={consecutive_errors}")
                return
            wait_s = decision.retry_after_seconds or 60
            sleep_interruptible(wait_s, logger, "video transient error backoff")


def poll_video_result(client: httpx.Client, cfg: Dict[str, Any], vcfg: Dict[str, Any], headers: Dict[str, str], video_id: str, task_id: Optional[str], logger: Logger) -> Dict[str, Any]:
    base_url = str(cfg.get("base_url", "https://apihub.agnes-ai.com")).rstrip("/")
    poll_interval = float(vcfg.get("poll_interval_seconds", 30))
    timeout = float(vcfg.get("poll_timeout_seconds", 2400))
    deadline = time.monotonic() + timeout
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        # Recommended endpoint: /agnesapi?video_id=<VIDEO_ID>
        try:
            last = request_json(client, "GET", f"{base_url}/agnesapi", headers=headers, params={"video_id": video_id, "model_name": vcfg.get("model", "agnes-video-v2.0")})
        except ApiError as exc:
            # Some IDs may require legacy task lookup; try once if task_id exists.
            if task_id:
                last = request_json(client, "GET", f"{base_url}/v1/videos/{task_id}", headers=headers)
            else:
                raise exc
        status = str(last.get("status") or "").lower()
        progress = last.get("progress")
        logger.log(f"[VIDEO] poll video_id={video_id} status={status} progress={progress}")
        if status == "completed":
            return last
        if status == "failed":
            raise ApiError(None, json.dumps(last, ensure_ascii=False), payload=last)
        sleep_interruptible(poll_interval, logger, "video polling")
    raise ApiError(408, f"video polling timeout after {timeout}s for video_id={video_id}", payload=last)


def run_image_phase(client: httpx.Client, cfg: Dict[str, Any], state: Dict[str, Any], state_path: Path, run_dir: Path, writers: Dict[str, JsonlWriter], logger: Logger, tz: ZoneInfo, dry_run: bool) -> None:
    phase = "image"
    icfg = cfg.get("image", {}) or {}
    if not icfg.get("enabled", True):
        logger.log("[IMAGE] disabled")
        return
    prompts = load_prompts(Path(icfg["prompt_file"]))
    success_ids = set(state.setdefault("image", {}).setdefault("success_ids", []))
    target_success = int(icfg.get("target_success", len(prompts)))
    interval = float(icfg.get("create_interval_seconds", 90))
    headers = {"Authorization": f"Bearer {os.environ.get(cfg['api_key_env'], 'DRY_RUN_KEY')}", "Content-Type": "application/json"}
    base_url = str(cfg.get("base_url", "https://apihub.agnes-ai.com")).rstrip("/")
    url = f"{base_url}/v1/images/generations"
    media_dir = run_dir / "media" / "images"
    logger.log(f"[IMAGE] start target_success={target_success} already_success={len(success_ids)} prompts={len(prompts)} interval={interval}s size={icfg.get('size')}")

    consecutive_errors = 0
    for prompt_obj in prompts:
        if len(success_ids) >= target_success:
            logger.log(f"[IMAGE] complete target_success={target_success}")
            return
        pid = str(prompt_obj["id"])
        if pid in success_ids:
            continue

        payload = {
            "model": str(icfg.get("model", "agnes-image-2.1-flash")),
            "prompt": str(prompt_obj["prompt"]),
            "size": str(icfg.get("size", "2048x2048")),
            "extra_body": {"response_format": str(icfg.get("response_format", "url"))},
        }
        started = now_tz(tz).isoformat(timespec="seconds")
        record: Dict[str, Any] = {"phase": phase, "prompt_id": pid, "category": prompt_obj.get("category"), "timestamp": started, "payload": payload}
        try:
            if dry_run:
                data = {"created": int(time.time()), "data": [{"url": f"dry://{pid}.png", "b64_json": None, "revised_prompt": None}]}
            else:
                data = request_json(client, "POST", url, headers=headers, json_body=payload)
            img_url = image_url_from_response(data)
            local_path = None
            if img_url and img_url.startswith("http") and bool(icfg.get("download_outputs", cfg.get("download_outputs", True))):
                try:
                    local_path = download_url(client, img_url, media_dir / f"{pid}", ".png")
                except Exception as dl_exc:
                    logger.log(f"[IMAGE] download failed id={pid}: {dl_exc}")

            success_ids.add(pid)
            state["image"]["success_ids"] = sorted(success_ids)
            save_state(state_path, state)
            writers["outputs"].write({**record, "event": "image_completed", "response": data, "output_url": img_url, "local_path": local_path, "finished_at": now_tz(tz).isoformat(timespec="seconds")})
            logger.log(f"[IMAGE] OK id={pid} success={len(success_ids)}/{target_success} url={img_url}")
            consecutive_errors = 0
            
            if not dry_run:
                sleep_interruptible(interval, logger, "next image create interval")
        except Exception as exc:
            decision = classify_error(exc, icfg)
            consecutive_errors += 1
            err_record = {**record, "event": "image_error", "error": str(exc), "error_class": decision.error_class, "http_status": getattr(exc, "status_code", None), "retry_after": getattr(exc, "retry_after", None), "decision": decision.__dict__, "finished_at": now_tz(tz).isoformat(timespec="seconds")}
            writers["errors"].write(err_record)
            logger.log(f"[IMAGE] ERR id={pid} class={decision.error_class} stop={decision.stop_phase} terminal={decision.terminal} {str(exc)[:240]}")
            state["image"]["error_count"] = int(state["image"].get("error_count", 0)) + 1
            save_state(state_path, state)
            if decision.stop_phase or consecutive_errors >= int(icfg.get("max_consecutive_errors", 1)):
                logger.log(f"[IMAGE] stop phase reason={decision.reason} consecutive_errors={consecutive_errors}")
                return
            wait_s = decision.retry_after_seconds or 60
            sleep_interruptible(wait_s, logger, "image transient error backoff")


def build_paths(cfg: Dict[str, Any], tz: ZoneInfo, run_stamp: Optional[str]) -> Tuple[Path, Path, Logger, Dict[str, JsonlWriter]]:
    today = today_str(tz)
    run_id = run_stamp or stamp(tz)
    out_root = Path(cfg.get("output_dir", "results")) / today / f"run_{run_id}"
    out_root.mkdir(parents=True, exist_ok=True)
    log_dir = Path(cfg.get("log_dir", "logs"))
    logger = Logger(log_dir / f"agnes_media_{today}_{run_id}.log")
    writers = {
        "outputs": JsonlWriter(out_root / "outputs.jsonl"),
        "errors": JsonlWriter(out_root / "errors.jsonl"),
    }
    return out_root, Path(cfg.get("state_file", "state/agnes_media_state.json")), logger, writers


def main() -> int:
    ap = argparse.ArgumentParser(description="Slow Agnes AI free-tier media harvester: video first, then images.")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--env-file", default=".env")
    ap.add_argument("--phase", choices=["all", "video", "image"], default="all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset-state", action="store_true")
    ap.add_argument("--run-stamp", help="Optional fixed run folder stamp")
    args = ap.parse_args()

    load_dotenv(args.env_file)
    cfg = load_yaml(Path(args.config))
    tz = ZoneInfo(str(cfg.get("timezone", "Asia/Taipei")))
    api_key_env = str(cfg.get("api_key_env", "AGNES_API_KEY"))
    cfg["api_key_env"] = api_key_env
    if not args.dry_run and not os.getenv(api_key_env):
        print(f"Missing env {api_key_env}. Create .env from .env.example.", file=sys.stderr)
        return 2

    run_dir, state_path, logger, writers = build_paths(cfg, tz, args.run_stamp)
    if args.reset_state and state_path.exists():
        state_path.unlink()
    state = load_state(state_path, today_str(tz))
    save_state(state_path, state)
    logger.log(f"[START] run_dir={run_dir} phase={args.phase} dry_run={args.dry_run}")

    http_cfg = cfg.get("http", {}) or {}
    timeout = httpx.Timeout(
        connect=float(http_cfg.get("connect_timeout_seconds", 30)),
        read=float(http_cfg.get("read_timeout_seconds", 900)),
        write=float(http_cfg.get("write_timeout_seconds", 60)),
        pool=float(http_cfg.get("pool_timeout_seconds", 30)),
    )
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if args.phase in ("all", "video"):
            run_video_phase(client, cfg, state, state_path, run_dir, writers, logger, tz, args.dry_run)
        if args.phase in ("all", "image"):
            run_image_phase(client, cfg, state, state_path, run_dir, writers, logger, tz, args.dry_run)

    logger.log("[DONE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
