#!/usr/bin/env python3
"""Promote the detector offline gallery from representative-only to full-corpus."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "tools" / "publish_detector_comparison.py"
TEST = ROOT / "tests" / "test_detector_comparison.py"

text = PUBLISHER.read_text(encoding="utf-8")
old = '''    preview_rows = choose_previews(comparisons, limit=args.preview_limit)
    preview_map: dict[str, str] = {}
    for row in preview_rows:
        digest = row["image_sha256"]
        original = find_original(yolox_root, digest)
        yolox_image = yolox_root / "package-root" / str(left[digest]["annotated_file"])
        nanodet_image = nanodet_root / "package-root" / str(right[digest]["annotated_file"])
        destination = comparison_root / "previews" / f"{digest}.jpg"
        render_tripanel(original, yolox_image, nanodet_image, row, destination)
        preview_map[digest] = f"../previews/{digest}.jpg"
    write_json(comparison_root / "entries.json", comparisons)
'''
new = '''    preview_rows = choose_previews(comparisons, limit=args.preview_limit)
    preview_ids = {row["image_sha256"] for row in preview_rows}
    preview_map: dict[str, str] = {}
    gallery_image_root = comparison_root / "gallery" / "images"
    # The downloadable offline gallery is evidence-complete: every canonical
    # image receives one Original | YOLOX | NanoDet tri-panel. Only the small,
    # deterministic representative subset is copied into versioned repo paths.
    for number, row in enumerate(comparisons, 1):
        digest = row["image_sha256"]
        original = find_original(yolox_root, digest)
        yolox_image = yolox_root / "package-root" / str(left[digest]["annotated_file"])
        nanodet_image = nanodet_root / "package-root" / str(right[digest]["annotated_file"])
        gallery_destination = gallery_image_root / f"{digest}.jpg"
        render_tripanel(original, yolox_image, nanodet_image, row, gallery_destination)
        preview_map[digest] = f"images/{digest}.jpg"
        if digest in preview_ids:
            preview_destination = comparison_root / "previews" / f"{digest}.jpg"
            preview_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(gallery_destination, preview_destination)
        print(
            f"[comparison {number}/{len(comparisons)}] {digest[:12]} "
            f"state={row['state']} disagreement={row['disagreement_score']:.3f}",
            flush=True,
        )
    gallery_images = sorted(gallery_image_root.glob("*.jpg"))
    if len(gallery_images) != len(comparisons):
        raise RuntimeError(
            f"Offline gallery coverage mismatch: expected {len(comparisons)}, "
            f"got {len(gallery_images)}"
        )
    write_json(comparison_root / "entries.json", comparisons)
'''
if old not in text:
    raise SystemExit("Publisher representative preview block did not match expected source")
text = text.replace(old, new, 1)
old_report = '''        "summary": summary,
        "disagreement_formula": "0.35*class + 0.25*count + 0.25*unmatched + 0.15*(1-mean_iou)",
'''
new_report = '''        "summary": summary,
        "offline_gallery_image_count": len(comparisons),
        "representative_preview_count": len(preview_rows),
        "disagreement_formula": "0.35*class + 0.25*count + 0.25*unmatched + 0.15*(1-mean_iou)",
'''
if old_report not in text:
    raise SystemExit("Publisher report block did not match expected source")
text = text.replace(old_report, new_report, 1)
old_gallery = '''    gallery = build_gallery(comparison_root, comparisons, preview_map)
    release_assets = output / "release-assets"
'''
new_gallery = '''    gallery = build_gallery(comparison_root, comparisons, preview_map)
    if len(list((gallery / "images").glob("*.jpg"))) != len(comparisons):
        raise RuntimeError("Packaged offline gallery is not full-corpus")
    release_assets = output / "release-assets"
'''
if old_gallery not in text:
    raise SystemExit("Publisher gallery packaging block did not match expected source")
text = text.replace(old_gallery, new_gallery, 1)
PUBLISHER.write_text(text, encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
anchor = '''    def test_artifact_validates_zip_hash_and_sidecar_coverage(self) -> None:
'''
addition = '''    def test_publisher_requires_full_corpus_offline_gallery(self) -> None:
        source = (ROOT / "tools" / "publish_detector_comparison.py").read_text(encoding="utf-8")
        self.assertIn("Offline gallery coverage mismatch", source)
        self.assertIn('"offline_gallery_image_count": len(comparisons)', source)
        self.assertIn('preview_map[digest] = f"images/{digest}.jpg"', source)
        self.assertIn("Only the small,", source)

'''
if addition not in test:
    if anchor not in test:
        raise SystemExit("Detector comparison test anchor not found")
    test = test.replace(anchor, addition + anchor, 1)
# Test module needs ROOT for the source-level invariant.
if "ROOT = Path(__file__).resolve().parents[1]" not in test:
    test = test.replace(
        "from tools.publish_detector_comparison import (",
        "ROOT = Path(__file__).resolve().parents[1]\n\nfrom tools.publish_detector_comparison import (",
        1,
    )
TEST.write_text(test, encoding="utf-8")
