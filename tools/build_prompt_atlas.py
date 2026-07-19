#!/usr/bin/env python3
"""Build, package, publish, and index a complete Prompt Repeatability Atlas."""
from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_atlas_core import (
    AtlasEntry,
    deduplicate_samples,
    locate_font,
    primary_roles,
    render_card,
    sample_public_dict,
    select_primary,
    temporal_quantiles,
)
from prompt_atlas_github import (
    collect_samples,
    download_archives,
    download_metadata,
    extract_images,
    group_candidates,
    publish_release,
    release_rows,
    resolve_source_tag,
)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gallery_html(report: dict[str, Any]) -> str:
    cards = []
    for entry in report.get("entries", []):
        cards.append(f'''<article><a href="primary/{html.escape(entry['primary_file'])}"><img loading="lazy" src="primary/{html.escape(entry['primary_file'])}" alt="{html.escape(entry['prompt_id'])} comparison"></a><div><strong>{html.escape(entry['prompt_id'])}</strong><span>{html.escape(entry['category'])} · {entry['sample_count']} samples</span><p>{html.escape(entry['prompt'])}</p></div></article>''')
    return f"""<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Prompt Repeatability Atlas</title><style>body{{margin:0;background:#07101d;color:#eef8ff;font:16px system-ui;padding:32px}}header{{max-width:1100px;margin:auto auto 28px}}main{{max-width:1400px;margin:auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}}article{{background:#0d1c2f;border:1px solid #315470;border-radius:16px;overflow:hidden}}img{{width:100%;display:block}}article div{{padding:16px}}strong,span{{display:block}}span,p{{color:#9cb5cc}}p{{font-size:14px;line-height:1.5}}</style><header><h1>Prompt Repeatability Atlas</h1><p>Source release: {html.escape(report.get('source_tag',''))}</p></header><main>{''.join(cards)}</main></html>"""


def create_zip(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path != destination:
                archive.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(destination) as archive:
        if bad := archive.testzip():
            raise IOError(f"Atlas ZIP verification failed: {bad}")


def build(rows: list[dict[str, Any]], source_tag: str, config: dict[str, Any], work: Path, output: Path) -> tuple[list[AtlasEntry], dict[str, Any]]:
    roots = download_metadata(rows, work / "metadata")
    all_samples = collect_samples(rows, roots)
    groups = group_candidates(all_samples, source_tag)
    extract_images(groups, download_archives(groups, work / "archives"), work / "extracted")
    entries: list[AtlasEntry] = []
    missing: list[dict[str, Any]] = []

    for cohort_id, raw in sorted(groups.items(), key=lambda item: (item[1][0].prompt_id, item[0])):
        samples = deduplicate_samples(raw, preferred_tag=source_tag)
        if len(samples) < 2:
            missing.append({"cohort_id": cohort_id, "prompt_id": raw[0].prompt_id, "metadata_samples": len(raw), "usable_unique_media": len(samples)})
            continue
        first = samples[0]
        primary = select_primary(samples, source_tag)
        primary_name = f"atlas-{first.prompt_id}-{cohort_id}-n{len(primary)}.jpg"
        render_card(output / "primary" / primary_name, prompt_id=first.prompt_id, category=first.category, prompt=first.prompt, model=first.model, cohort_id=cohort_id, samples=primary, roles=primary_roles(primary, source_tag), config=config)

        extended_name = None
        extended = []
        if len(samples) >= int(config.get("extended_min_samples", 5)):
            extended = temporal_quantiles(samples, min(int(config.get("extended_max_samples", 8)), len(samples)))
            extended_name = f"atlas-{first.prompt_id}-{cohort_id}-extended-n{len(extended)}.jpg"
            render_card(output / "extended" / extended_name, prompt_id=first.prompt_id, category=first.category, prompt=first.prompt, model=first.model, cohort_id=cohort_id, samples=extended, roles=[f"Temporal {index + 1}/{len(extended)}" for index in range(len(extended))], config=config, extended=True)

        sidecar_name = f"atlas-{first.prompt_id}-{cohort_id}.json"
        save_json(output / "sidecars" / sidecar_name, {
            "schema_version": 1,
            "source_tag": source_tag,
            "prompt_id": first.prompt_id,
            "category": first.category,
            "prompt": first.prompt,
            "model": first.model,
            "settings": first.settings,
            "cohort_id": cohort_id,
            "sample_count": len(samples),
            "selection_policy": {"primary": "historical anchors plus current", "extended": "up to eight temporal quantiles", "deduplication": "exact SHA-256"},
            "all_samples": [sample_public_dict(item) for item in samples],
            "primary_samples": [sample_public_dict(item) for item in primary],
            "extended_samples": [sample_public_dict(item) for item in extended],
            "rendering": {"fit": "contain", "cell_size": config.get("cell_size", 960), "font": str(locate_font(config) or "Pillow default")},
        })
        entries.append(AtlasEntry(first.prompt_id, first.category, first.prompt, first.model, cohort_id, len(samples), source_tag, primary_name, sidecar_name, extended_name, [sample_public_dict(item) for item in primary], [sample_public_dict(item) for item in extended]))

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_tag": source_tag,
        "release_count_scanned": len(rows),
        "metadata_image_samples": len(all_samples),
        "candidate_cohorts": len(groups),
        "comparable_prompts": len(entries),
        "missing_or_duplicate_media": missing,
        "entries": [asdict(entry) for entry in entries],
    }
    output.mkdir(parents=True, exist_ok=True)
    save_json(output / "atlas-report.json", report)
    (output / "index.html").write_text(gallery_html(report), encoding="utf-8")
    create_zip(output, output / "prompt-repeatability-atlas.zip")
    return entries, report


def write_pages_index(path: Path, report: dict[str, Any], publication: dict[str, Any] | None) -> None:
    assets = publication.get("assets", {}) if publication else {}
    entries = [{
        "prompt_id": item["prompt_id"],
        "category": item["category"],
        "prompt": item["prompt"],
        "model": item["model"],
        "cohort_id": item["cohort_id"],
        "sample_count": item["sample_count"],
        "primary_url": assets.get(item["primary_file"]),
        "has_extended": bool(item.get("extended_file")),
    } for item in report.get("entries", [])]
    save_json(path, {
        "schema_version": 1,
        "status": "published" if publication else ("no_comparable_prompts" if not entries else "built_not_published"),
        "generated_at_utc": report.get("generated_at_utc"),
        "source_tag": report.get("source_tag"),
        "comparable_prompts": len(entries),
        "analysis_tag": publication.get("analysis_tag") if publication else None,
        "analysis_url": publication.get("analysis_url") if publication else None,
        "archive_url": publication.get("archive_url") if publication else None,
        "report_url": publication.get("report_url") if publication else None,
        "highlights": publication.get("highlights", []) if publication else [],
        "entries": entries,
    })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tag", default=os.environ.get("SOURCE_TAG", "latest"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--config", type=Path, default=Path("visual-analysis/config.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("visual-analysis/output"))
    parser.add_argument("--pages-index", type=Path, default=Path("web/public/data/visual-analysis.json"))
    parser.add_argument("--publish", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config, {})
    rows = release_rows()
    source_tag = resolve_source_tag(rows, args.source_tag)
    with tempfile.TemporaryDirectory(prefix="prompt-atlas-") as temp:
        entries, report = build(rows, source_tag, config, Path(temp), args.output_dir)
    publication = publish_release(args.repo, source_tag, args.output_dir, entries, config) if args.publish and entries else None
    write_pages_index(args.pages_index, report, publication)
    print(json.dumps({"source_tag": source_tag, "comparable_prompts": len(entries), "analysis_tag": publication.get("analysis_tag") if publication else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
