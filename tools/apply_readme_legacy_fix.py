#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tools" / "update_readme_summary.py"
text = path.read_text(encoding="utf-8")
old = '''                    files = run.get("files") if isinstance(run.get("files"), list) else []
                    archived = media_counts_from_file_records(files)
                    images += archived["images"]
                    videos += archived["videos"]
'''
new = '''                    has_file_records = isinstance(run.get("files"), list)
                    files = run.get("files") if has_file_records else []
                    if has_file_records:
                        # Explicit file records are authoritative, including an
                        # explicit metadata-only run whose archived media count is zero.
                        archived = media_counts_from_file_records(files)
                        images += archived["images"]
                        videos += archived["videos"]
                    else:
                        # Legacy manifests predate file records. Preserve backwards
                        # compatibility while new manifests use archived-file truth.
                        stats = run.get("stats") if isinstance(run.get("stats"), dict) else {}
                        images += int(stats.get("archived_images", stats.get("image_completed", 0)) or 0)
                        videos += int(stats.get("archived_videos", stats.get("video_completed", 0)) or 0)
'''
if new not in text:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one README summary block, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink()
