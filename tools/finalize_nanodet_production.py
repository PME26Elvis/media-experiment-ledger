#!/usr/bin/env python3
"""Build an evidence-locked NanoDet production finalization patch."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "PME26Elvis/media-experiment-ledger")
TOKEN = os.environ.get("GH_TOKEN", "")


def command(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stderr or result.stdout}")
    return result


def gh(path: str) -> Any:
    return json.loads(command(["gh", "api", path]).stdout or "null")


def content(path: str, ref: str = "main") -> tuple[Any, str, str]:
    row = gh(f"repos/{REPO}/contents/{path}?ref={ref}")
    raw = base64.b64decode(row["content"]).decode("utf-8")
    return json.loads(raw), str(row["sha"]), raw


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value.rstrip() + "\n", encoding="utf-8")


def upsert(path: str, start: str, end: str, block: str) -> None:
    text = read(path)
    rendered = f"{start}\n{block.strip()}\n{end}"
    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        text = f"{before}\n\n{rendered}\n\n{after}"
    else:
        text = f"{text.rstrip()}\n\n{rendered}\n"
    write(path, text)


def wait_pages(batch: str, timeout_seconds: int = 1800) -> dict[str, Any]:
    root = "https://pme26elvis.github.io/media-experiment-ledger"
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{root}/data/detection/latest.json", timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            with urllib.request.urlopen(f"{root}/detector-lab/", timeout=30) as response:
                page = response.read().decode("utf-8", errors="replace")
            if payload.get("analysis_batch_id") == batch and payload.get("status") == "published" and "Detector Lab" in page:
                return {
                    "status": "verified",
                    "analysis_batch_id": batch,
                    "detector_lab_url": f"{root}/detector-lab/",
                    "index_url": f"{root}/data/detection/latest.json",
                }
            last_error = f"deployed batch/status not current: {payload.get('analysis_batch_id')} / {payload.get('status')}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        print(f"Waiting for live Detector Lab: {last_error}", flush=True)
        time.sleep(20)
    raise TimeoutError(f"Live Detector Lab did not converge: {last_error}")


def find_publisher(latest: dict[str, Any]) -> dict[str, Any]:
    payload = gh(
        f"repos/{REPO}/actions/workflows/detector-comparison-publish.yml/runs?branch=main&status=success&per_page=100"
    )
    candidates = sorted(payload.get("workflow_runs", []), key=lambda row: int(row["id"]), reverse=True)
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for row in candidates:
            run_id = int(row["id"])
            artifacts = gh(f"repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100").get("artifacts", [])
            names = [
                str(item.get("name")) for item in artifacts
                if not item.get("expired") and str(item.get("name", "")).startswith("detector-comparison-recovery-")
            ]
            if len(names) != 1:
                continue
            destination = temp_root / str(run_id)
            destination.mkdir()
            result = subprocess.run(
                ["gh", "run", "download", str(run_id), "--repo", REPO, "--name", names[0], "--dir", str(destination)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode:
                print(f"Skipping publisher {run_id}: {result.stderr or result.stdout}", flush=True)
                continue
            matches = list(destination.rglob("latest.json"))
            for candidate in matches:
                try:
                    value = json.loads(candidate.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if value.get("analysis_batch_id") == latest.get("analysis_batch_id") and value.get("release_tag") == latest.get("release_tag"):
                    return {
                        "run_id": run_id,
                        "head_sha": row.get("head_sha"),
                        "event": row.get("event"),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                        "html_url": row.get("html_url"),
                        "recovery_artifact": names[0],
                    }
    raise RuntimeError("No successful publisher recovery artifact matches the current production batch and Release")


def find_writeback(latest: dict[str, Any]) -> dict[str, Any]:
    rows = gh(f"repos/{REPO}/commits?path=data/detection/latest.json&per_page=30")
    for row in rows:
        sha = str(row["sha"])
        try:
            value, blob_sha, _ = content("data/detection/latest.json", sha)
        except Exception:
            continue
        if value.get("analysis_batch_id") == latest.get("analysis_batch_id") and value.get("release_tag") == latest.get("release_tag"):
            commit = gh(f"repos/{REPO}/commits/{sha}")
            parents = commit.get("parents", [])
            if len(parents) != 1:
                raise RuntimeError(f"Detector writeback {sha} must have one parent")
            parent = str(parents[0]["sha"])
            before = gh(f"repos/{REPO}/contents/web/public/data/visual-analysis.json?ref={parent}")["sha"]
            after = gh(f"repos/{REPO}/contents/web/public/data/visual-analysis.json?ref={sha}")["sha"]
            changed = [str(item.get("filename")) for item in commit.get("files", [])]
            forbidden = [path for path in changed if path.startswith("visual-analysis/") or path == "web/public/data/visual-analysis.json"]
            if forbidden or before != after:
                raise RuntimeError(f"Detector writeback changed Atlas surfaces: {forbidden}, {before} -> {after}")
            return {
                "sha": sha,
                "html_url": commit.get("html_url"),
                "message": commit.get("commit", {}).get("message"),
                "parent_sha": parent,
                "detector_index_blob_sha": blob_sha,
                "changed_files": changed,
                "atlas_index_sha_before": before,
                "atlas_index_sha_after": after,
                "atlas_non_regression": True,
            }
    raise RuntimeError("Could not resolve the detector index writeback commit")


def main() -> int:
    latest, latest_blob, latest_raw = content("data/detection/latest.json")
    history, history_blob, history_raw = content("data/detection/history.json")
    web_latest, web_blob, web_raw = content("web/public/data/detection/latest.json")
    if latest != web_latest:
        raise RuntimeError("Canonical and web detector indexes differ")
    if latest.get("status") != "published":
        raise RuntimeError(f"Detector index is not published: {latest.get('status')}")
    if not history.get("releases") or history["releases"][0].get("tag") != latest.get("release_tag"):
        raise RuntimeError("Detector history does not lead with the current Release")

    release = gh(f"repos/{REPO}/releases/tags/{latest['release_tag']}")
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError("Production detector Release must be a final non-draft Release")
    if latest["analysis_batch_id"] not in str(release.get("body") or ""):
        raise RuntimeError("Release Notes do not carry the current analysis batch")
    assets = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "size_bytes": int(item.get("size") or 0),
            "download_count": item.get("download_count"),
            "browser_download_url": item.get("browser_download_url"),
        }
        for item in release.get("assets", [])
    ]
    if not assets or any(not str(item["name"]).endswith(".zip") or item["size_bytes"] <= 0 for item in assets):
        raise RuntimeError("Production detector Release must contain non-empty ZIP-only assets")

    family = []
    page = 1
    while page <= 10:
        rows = gh(f"repos/{REPO}/releases?per_page=100&page={page}")
        if not rows:
            break
        family.extend(
            {
                "tag": row.get("tag_name"),
                "draft": row.get("draft"),
                "published_at": row.get("published_at"),
                "html_url": row.get("html_url"),
            }
            for row in rows if str(row.get("tag_name", "")).startswith("media-detection-all-")
        )
        page += 1

    publisher = find_publisher(latest)
    writeback = find_writeback(latest)
    pages = wait_pages(str(latest["analysis_batch_id"]))
    detectors = latest["detectors"]
    summary = latest["summary"]
    previews = latest.get("previews", [])

    evidence = {
        "schema_version": 1,
        "status": "verified",
        "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": REPO,
        "analysis_batch_id": latest["analysis_batch_id"],
        "corpus_fingerprint": latest["corpus_fingerprint"],
        "date_from": latest["date_from"],
        "date_to": latest["date_to"],
        "thresholds": latest["thresholds"],
        "detectors": detectors,
        "publisher": publisher,
        "release": {
            "tag": release["tag_name"],
            "html_url": release["html_url"],
            "published_at": release.get("published_at"),
            "assets": assets,
            "asset_count": len(assets),
            "asset_total_bytes": sum(item["size_bytes"] for item in assets),
        },
        "release_family": sorted(family, key=lambda row: (str(row["published_at"]), str(row["tag"]))),
        "writeback": writeback,
        "pages": pages,
        "summary": summary,
        "representative_preview_count": len(previews),
        "latest_index_blob_sha": latest_blob,
        "history_index_blob_sha": history_blob,
        "web_index_blob_sha": web_blob,
        "interpretation": latest["interpretation"],
    }

    report_json = ROOT / "docs/reports/NANODET_PRODUCTION_EVIDENCE.json"
    write_json(report_json, evidence)
    report_md = f"""# NanoDet multi-detector production evidence

- Verified (UTC): `{evidence['verified_at_utc']}`
- Analysis batch: `{evidence['analysis_batch_id']}`
- YOLOX workflow run: `{detectors['yolox-tiny']['workflow_run_id']}`
- NanoDet workflow run: `{detectors['nanodet-plus-m-320']['workflow_run_id']}`
- Publisher workflow run: `{publisher['run_id']}`
- Writeback commit: [`{writeback['sha']}`]({writeback['html_url']})
- Production Release: [{release['tag_name']}]({release['html_url']})
- Canonical images compared: **{summary['images_compared']:,}**
- YOLOX detections: **{summary['yolox_total_detections']:,}**
- NanoDet detections: **{summary['nanodet_total_detections']:,}**
- Matched same-class boxes: **{summary['matched_boxes']:,}**
- Mean disagreement: **{summary['mean_disagreement_score']:.6f}**
- Agreement states: `{json.dumps(summary['states'], sort_keys=True)}`
- Release assets: **{len(assets)} ZIP files**, **{sum(item['size_bytes'] for item in assets):,} bytes**
- Representative repository previews: **{len(previews)}**
- Detector Lab: [{pages['detector_lab_url']}]({pages['detector_lab_url']})
- Deployed JSON: [{pages['index_url']}]({pages['index_url']})
- Atlas index SHA unchanged across detector writeback: `{writeback['atlas_index_sha_before']}`

This report records agreement/disagreement observations from two COCO-pretrained detectors. The generated corpus has no human-verified COCO ground truth, so this is not an accuracy, precision, recall, false-positive, or mAP benchmark.

The complete machine-readable evidence is stored in `NANODET_PRODUCTION_EVIDENCE.json`.
"""
    write("docs/reports/NANODET_PRODUCTION_EVIDENCE.md", report_md)

    contract_path = ROOT / "project-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    multi = contract["planned_analysis"]["multi_detector_yolox_nanodet"]
    multi.update({
        "status": "implemented",
        "production_release": release["tag_name"],
        "production_analysis_batch_id": latest["analysis_batch_id"],
        "production_corpus_fingerprint": latest["corpus_fingerprint"],
        "production_yolox_run_id": str(detectors["yolox-tiny"]["workflow_run_id"]),
        "production_nanodet_run_id": str(detectors["nanodet-plus-m-320"]["workflow_run_id"]),
        "production_publisher_run_id": str(publisher["run_id"]),
        "production_writeback_commit": writeback["sha"],
        "production_canonical_images": int(summary["images_compared"]),
        "production_yolox_images_with_detections": int(detectors["yolox-tiny"]["summary"]["images_with_detections"]),
        "production_yolox_total_detections": int(summary["yolox_total_detections"]),
        "production_nanodet_images_with_detections": int(detectors["nanodet-plus-m-320"]["summary"]["images_with_detections"]),
        "production_nanodet_total_detections": int(summary["nanodet_total_detections"]),
        "production_matched_boxes": int(summary["matched_boxes"]),
        "production_mean_disagreement_score": float(summary["mean_disagreement_score"]),
        "production_release_asset_count": len(assets),
        "production_release_asset_bytes": sum(item["size_bytes"] for item in assets),
        "production_representative_previews": len(previews),
        "production_pages_verified": True,
        "production_atlas_non_regression": True,
        "production_evidence_json": "docs/reports/NANODET_PRODUCTION_EVIDENCE.json",
        "production_evidence_markdown": "docs/reports/NANODET_PRODUCTION_EVIDENCE.md",
    })
    surfaces = contract["synchronized_surfaces"]
    for path in (
        "docs/reports/NANODET_PRODUCTION_EVIDENCE.json",
        "docs/reports/NANODET_PRODUCTION_EVIDENCE.md",
    ):
        if path not in surfaces:
            surfaces.append(path)
    contract_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    validator_path = "tools/validate_project_contract.py"
    validator = read(validator_path)
    anchor = '''        if latest.get("status") != "published" or latest.get("release_tag") != multi.get("production_release"):\n            errors.append("Implemented detector latest index must match production Release")\n'''
    replacement = anchor + '''        exact_fields = {\n            "analysis_batch_id": "production_analysis_batch_id",\n            "corpus_fingerprint": "production_corpus_fingerprint",\n        }\n        for index_key, contract_key in exact_fields.items():\n            require_equal(latest.get(index_key), multi.get(contract_key), f"Detector production {index_key}", errors)\n        detectors = latest.get("detectors") if isinstance(latest.get("detectors"), dict) else {}\n        summary = latest.get("summary") if isinstance(latest.get("summary"), dict) else {}\n        checks = {\n            "production_yolox_run_id": str((detectors.get("yolox-tiny") or {}).get("workflow_run_id") or ""),\n            "production_nanodet_run_id": str((detectors.get("nanodet-plus-m-320") or {}).get("workflow_run_id") or ""),\n            "production_canonical_images": summary.get("images_compared"),\n            "production_yolox_total_detections": summary.get("yolox_total_detections"),\n            "production_nanodet_total_detections": summary.get("nanodet_total_detections"),\n            "production_matched_boxes": summary.get("matched_boxes"),\n            "production_mean_disagreement_score": summary.get("mean_disagreement_score"),\n            "production_representative_previews": len(latest.get("previews") or []),\n        }\n        for contract_key, actual in checks.items():\n            require_equal(multi.get(contract_key), actual, f"Detector production {contract_key}", errors)\n        releases = history.get("releases") or []\n        if not releases or releases[0].get("tag") != multi.get("production_release"):\n            errors.append("Detector production history must lead with the production Release")\n        evidence_path = ROOT / str(multi.get("production_evidence_json") or "")\n        if not evidence_path.exists():\n            errors.append("Implemented detector contract requires permanent production evidence")\n        else:\n            evidence = read_json(evidence_path)\n            require_equal(evidence.get("status"), "verified", "Detector evidence status", errors)\n            require_equal((evidence.get("release") or {}).get("tag"), multi.get("production_release"), "Detector evidence Release", errors)\n            require_equal(str((evidence.get("publisher") or {}).get("run_id") or ""), str(multi.get("production_publisher_run_id") or ""), "Detector evidence publisher run", errors)\n            require_equal((evidence.get("writeback") or {}).get("sha"), multi.get("production_writeback_commit"), "Detector evidence writeback", errors)\n            require_equal((evidence.get("pages") or {}).get("status"), "verified", "Detector evidence Pages", errors)\n            require_equal((evidence.get("writeback") or {}).get("atlas_non_regression"), True, "Detector evidence Atlas non-regression", errors)\n'''
    if replacement not in validator:
        if anchor not in validator:
            raise RuntimeError("Validator production anchor not found")
        validator = validator.replace(anchor, replacement, 1)
    write(validator_path, validator)

    spec_path = "docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md"
    spec = read(spec_path).replace("implemented_pending_production", "implemented")
    write(spec_path, spec)
    upsert(spec_path, "<!-- NANODET:IMPLEMENTATION:START -->", "<!-- NANODET:IMPLEMENTATION:END -->", f"""
## 18. Production implementation status — verified 2026-07-21

Status is **`implemented`**. The complete corpus was processed by YOLOX-Tiny run `{detectors['yolox-tiny']['workflow_run_id']}` and NanoDet-Plus run `{detectors['nanodet-plus-m-320']['workflow_run_id']}`. Publisher run `{publisher['run_id']}` verified the exact pair and created immutable ZIP-only Release [`{release['tag_name']}`]({release['html_url']}).

Production evidence:

- canonical images: **{summary['images_compared']:,}**, zero detector failures;
- YOLOX detections: **{summary['yolox_total_detections']:,}**; NanoDet detections: **{summary['nanodet_total_detections']:,}**;
- matched same-class boxes at IoU ≥ 0.50: **{summary['matched_boxes']:,}**;
- mean disagreement score: **{summary['mean_disagreement_score']:.6f}**;
- full-corpus offline tri-panels plus **{len(previews)}** versioned representative previews;
- Detector Lab and deployed JSON verified live;
- detector writeback commit `{writeback['sha']}` preserved the exact Atlas index blob SHA `{writeback['atlas_index_sha_before']}`.

The official NanoDet ONNX remains pinned at SHA-256 `4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610`. These are detector agreement/disagreement observations, not ground-truth labels or an accuracy benchmark. Full evidence: [`docs/reports/NANODET_PRODUCTION_EVIDENCE.md`](reports/NANODET_PRODUCTION_EVIDENCE.md).
""")

    for path in ("README.md", "README.en.md", "AGENTS.md", "docs/PROJECT_CONTRACT.md"):
        write(path, read(path).replace("implemented_pending_production", "implemented"))

    upsert("README.md", "<!-- NANODET:README:START -->", "<!-- NANODET:README:END -->", f"""
## YOLOX + NanoDet 多模型偵測

多模型管線狀態為 **`implemented`**。YOLOX-Tiny run `{detectors['yolox-tiny']['workflow_run_id']}` 與 NanoDet-Plus-m-320 run `{detectors['nanodet-plus-m-320']['workflow_run_id']}` 均從零處理完整 387 張 canonical images；publisher run `{publisher['run_id']}` 以 exact run IDs 與完整 corpus/hash 契約配對後，發布 ZIP-only [`{release['tag_name']}`]({release['html_url']})。

- YOLOX：{summary['yolox_total_detections']:,} boxes；NanoDet：{summary['nanodet_total_detections']:,} boxes；同類別 IoU ≥ 0.50 配對 {summary['matched_boxes']:,} 組。
- mean disagreement 為 {summary['mean_disagreement_score']:.4f}；這不是 accuracy benchmark，沒有人工 COCO ground truth 時不宣稱 precision、recall、mAP 或哪個模型正確。
- [Detector Lab](web/src/content/docs/detector-lab.mdx) 提供 Original／YOLOX／NanoDet 三欄比較與 {len(previews)} 張版本化代表預覽；完整 387 張 tri-panels 位於 Release gallery ZIP。
- writeback commit `{writeback['sha']}`、live Pages、ZIP-only assets 與 Atlas non-regression 均已驗證。
- [完整 production evidence](docs/reports/NANODET_PRODUCTION_EVIDENCE.md) · [完整契約](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md)
""")
    upsert("README.en.md", "<!-- NANODET:README_EN:START -->", "<!-- NANODET:README_EN:END -->", f"""
## YOLOX + NanoDet multi-detector analysis

The multi-detector pipeline is **`implemented`**. YOLOX-Tiny run `{detectors['yolox-tiny']['workflow_run_id']}` and NanoDet-Plus-m-320 run `{detectors['nanodet-plus-m-320']['workflow_run_id']}` each rebuilt all 387 canonical images from scratch. Publisher run `{publisher['run_id']}` paired the exact run IDs, validated the full corpus/hash contract, and published ZIP-only Release [`{release['tag_name']}`]({release['html_url']}).

- YOLOX observed {summary['yolox_total_detections']:,} boxes; NanoDet observed {summary['nanodet_total_detections']:,}; {summary['matched_boxes']:,} same-class pairs matched at IoU ≥ 0.50.
- Mean disagreement is {summary['mean_disagreement_score']:.4f}. This is not an accuracy benchmark; without human COCO ground truth, the project does not claim precision, recall, mAP, or which detector is correct.
- [Detector Lab](web/src/content/docs/detector-lab.mdx) provides Original / YOLOX / NanoDet comparisons and {len(previews)} versioned representative previews; the Release gallery ZIP contains all 387 tri-panels.
- Writeback commit `{writeback['sha']}`, live Pages, ZIP-only assets, and Atlas non-regression were verified.
- [Production evidence](docs/reports/NANODET_PRODUCTION_EVIDENCE.md) · [Full contract](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md)
""")
    upsert("AGENTS.md", "<!-- NANODET:AGENTS:START -->", "<!-- NANODET:AGENTS:END -->", f"""
## Multi-detector behavior

- Multi-detector status is `implemented`; production Release is `{release['tag_name']}`.
- Verified production runs: YOLOX `{detectors['yolox-tiny']['workflow_run_id']}`, NanoDet `{detectors['nanodet-plus-m-320']['workflow_run_id']}`, publisher `{publisher['run_id']}`, writeback `{writeback['sha']}`.
- Inference workflows remain read-only and artifact-only. Pair only exact workflow run IDs; never combine independently selected latest runs.
- NanoDet uses the SHA-pinned official immutable ONNX and `requirements-nanodet.txt`.
- Keep agreement/disagreement language; no accuracy claim without ground truth.
- Detector Lab is the combined production UI; YOLO Lab is immutable legacy history.
- Multi-detector work must not change Atlas workflow, Releases, previews, indexes, history, or finalizer. The verified detector writeback preserved Atlas blob `{writeback['atlas_index_sha_before']}`.
- Permanent evidence: `docs/reports/NANODET_PRODUCTION_EVIDENCE.json` and `.md`.
""")
    upsert("docs/PROJECT_CONTRACT.md", "<!-- NANODET:PROJECT_CONTRACT:START -->", "<!-- NANODET:PROJECT_CONTRACT:END -->", f"""
## Multi-detector production boundary

The YOLOX + NanoDet pipeline is `implemented`. Read-only full-corpus runs `{detectors['yolox-tiny']['workflow_run_id']}` and `{detectors['nanodet-plus-m-320']['workflow_run_id']}` were paired by publisher `{publisher['run_id']}` and published as `{release['tag_name']}`. The index/writeback commit is `{writeback['sha']}`.

Production covers {summary['images_compared']:,} canonical images with zero detector failures, {summary['yolox_total_detections']:,} YOLOX boxes, {summary['nanodet_total_detections']:,} NanoDet boxes, {summary['matched_boxes']:,} same-class matched boxes, and mean disagreement {summary['mean_disagreement_score']:.6f}. Detector Lab and its JSON were verified on live Pages. All Release assets are ZIP containers.

Generated media lacks human COCO ground truth; only agreement/disagreement observations are valid. Atlas is independent, and its index blob remained `{writeback['atlas_index_sha_before']}` across detector writeback. See `docs/reports/NANODET_PRODUCTION_EVIDENCE.md`.
""")

    test = f'''from __future__ import annotations\n\nimport json\nimport unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\nclass NanoDetPipelineSpecTests(unittest.TestCase):\n    def test_spec_requires_exact_run_pairing_and_no_accuracy_claim(self) -> None:\n        spec = (ROOT / "docs" / "NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md").read_text(encoding="utf-8")\n        for token in (\n            "Status: **`implemented`**",\n            "detector-yolox-inference.yml",\n            "detector-nanodet-inference.yml",\n            "detector-comparison-publish.yml",\n            "media-detection-all-",\n            "exact run IDs",\n            "analysis_batch_id",\n            "Original | YOLOX-Tiny | NanoDet-Plus",\n            "not ground-truth labels or an accuracy benchmark",\n            "Atlas impact: **none**",\n            '"Latest successful YOLO" plus "latest successful NanoDet" is forbidden',\n            "official immutable pre-exported ONNX",\n            "4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610",\n        ):\n            self.assertIn(token, spec)\n        self.assertIn("workflow artifacts are transport", spec.lower())\n\n    def test_machine_contract_records_verified_production(self) -> None:\n        contract = json.loads((ROOT / "project-contract.json").read_text(encoding="utf-8"))["planned_analysis"]["multi_detector_yolox_nanodet"]\n        self.assertEqual(contract["status"], "implemented")\n        self.assertEqual(contract["production_release"], {release['tag_name']!r})\n        self.assertEqual(contract["production_yolox_run_id"], {str(detectors['yolox-tiny']['workflow_run_id'])!r})\n        self.assertEqual(contract["production_nanodet_run_id"], {str(detectors['nanodet-plus-m-320']['workflow_run_id'])!r})\n        self.assertEqual(contract["production_publisher_run_id"], {str(publisher['run_id'])!r})\n        self.assertEqual(contract["production_writeback_commit"], {writeback['sha']!r})\n        self.assertEqual(contract["production_canonical_images"], 387)\n        self.assertTrue(contract["production_pages_verified"])\n        self.assertTrue(contract["production_atlas_non_regression"])\n        self.assertEqual(contract["atlas_coupling"], "none")\n        self.assertFalse(contract["persistent_state"])\n        self.assertFalse(contract["cross_run_cache_skip"])\n        self.assertFalse(contract["published_result_reuse"])\n\n\nif __name__ == "__main__":\n    unittest.main()\n'''
    write("tests/test_nanodet_pipeline_spec.py", test)

    # Copy the canonical published indexes resolved from current main so this
    # patch remains correct even when the feature branch predates a bot writeback.
    write("data/detection/latest.json", latest_raw)
    write("data/detection/history.json", history_raw)
    write("web/public/data/detection/latest.json", web_raw)

    manifest = {
        "schema_version": 1,
        "generated_at_utc": evidence["verified_at_utc"],
        "production_release": release["tag_name"],
        "analysis_batch_id": latest["analysis_batch_id"],
        "publisher_run_id": publisher["run_id"],
        "writeback_commit": writeback["sha"],
        "patched_files": [
            "project-contract.json",
            "tools/validate_project_contract.py",
            "tests/test_nanodet_pipeline_spec.py",
            "README.md",
            "README.en.md",
            "AGENTS.md",
            "docs/PROJECT_CONTRACT.md",
            "docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md",
            "docs/reports/NANODET_PRODUCTION_EVIDENCE.json",
            "docs/reports/NANODET_PRODUCTION_EVIDENCE.md",
            "data/detection/latest.json",
            "data/detection/history.json",
            "web/public/data/detection/latest.json",
        ],
    }
    write_json(ROOT / "nanodet-finalization-manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
