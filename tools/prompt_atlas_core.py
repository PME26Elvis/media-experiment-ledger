"""Pure data, selection, and rendering primitives for Prompt Repeatability Atlas."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps

MEDIA_TAG_RE = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})(?:-s\d{2})?$")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class Sample:
    prompt_id: str
    category: str
    prompt: str
    model: str
    settings: dict[str, Any]
    cohort_id: str
    source_tag: str
    release_published_at: str
    run_id: str
    timestamp: str
    finished_at: str
    local_path: str | None
    seed: Any = None
    archive_name: str | None = None
    archive_member: str | None = None
    extracted_path: str | None = None
    sha256: str | None = None
    width: int | None = None
    height: int | None = None

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        return (
            self.finished_at or self.timestamp or self.release_published_at,
            self.source_tag,
            self.run_id,
            self.local_path or "",
        )


@dataclass
class AtlasEntry:
    prompt_id: str
    category: str
    prompt: str
    model: str
    cohort_id: str
    sample_count: int
    source_tag: str
    primary_file: str
    sidecar_file: str
    extended_file: str | None
    selected_primary: list[dict[str, Any]] = field(default_factory=list)
    selected_extended: list[dict[str, Any]] = field(default_factory=list)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any, length: int = 16) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()[:length]


def normalized_settings(payload: Any) -> dict[str, Any]:
    """Keep appearance-relevant request settings while excluding prompt/transport fields."""
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in sorted(payload.items()):
        if key in {"prompt", "response_format"}:
            continue
        if key == "extra_body" and isinstance(value, dict):
            reduced = {k: v for k, v in sorted(value.items()) if k != "response_format"}
            if reduced:
                normalized[key] = reduced
        else:
            normalized[key] = value
    return normalized


def cohort_identity(prompt_id: str, model: str, settings: dict[str, Any]) -> str:
    return stable_hash({"prompt_id": prompt_id, "model": model, "settings": settings})


def member_matches(member: str, prompt_id: str) -> bool:
    path = PurePosixPath(member)
    return path.suffix.lower() in IMAGE_SUFFIXES and path.stem == prompt_id and "images" in path.parts


def deduplicate_samples(samples: Sequence[Sample], preferred_tag: str | None = None) -> list[Sample]:
    """Keep one verified sample per byte digest, preferring the source Release on ties."""
    groups: dict[str, list[Sample]] = {}
    for sample in sorted(samples, key=lambda item: item.sort_key):
        if sample.extracted_path and sample.sha256:
            groups.setdefault(sample.sha256, []).append(sample)
    output: list[Sample] = []
    for digest_samples in groups.values():
        preferred = [item for item in digest_samples if preferred_tag and item.source_tag == preferred_tag]
        output.append((preferred or digest_samples)[-1 if preferred else 0])
    return sorted(output, key=lambda item: item.sort_key)


def temporal_quantiles(samples: Sequence[Sample], count: int) -> list[Sample]:
    ordered = sorted(samples, key=lambda item: item.sort_key)
    if count >= len(ordered):
        return ordered
    if count <= 1:
        return [ordered[-1]]
    indices = [round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)]
    selected: list[Sample] = []
    for index in indices:
        if ordered[index] not in selected:
            selected.append(ordered[index])
    for item in ordered:
        if len(selected) >= count:
            break
        if item not in selected:
            selected.append(item)
    return sorted(selected[:count], key=lambda item: item.sort_key)


def select_primary(samples: Sequence[Sample], source_tag: str) -> list[Sample]:
    ordered = sorted(samples, key=lambda item: item.sort_key)
    if len(ordered) <= 3:
        return ordered
    current = ([item for item in ordered if item.source_tag == source_tag] or [ordered[-1]])[-1]
    history = [item for item in ordered if item is not current]
    selected = temporal_quantiles(history, min(3, len(history))) + [current]
    unique: list[Sample] = []
    for item in selected + ordered:
        if item not in unique:
            unique.append(item)
        if len(unique) == 4:
            break
    unique.sort(key=lambda item: item.sort_key)
    if current in unique:
        unique.remove(current)
        unique.append(current)
    return unique


def primary_roles(samples: Sequence[Sample], source_tag: str) -> list[str]:
    if len(samples) == 2:
        return ["Historical", "Current" if samples[-1].source_tag == source_tag else "Latest"]
    if len(samples) == 3:
        return ["Earliest", "Historical", "Current" if samples[-1].source_tag == source_tag else "Latest"]
    return ["Earliest", "Mid-history", "Latest prior", "Current"]


def grid_shape(sample_count: int, *, extended: bool = False) -> tuple[int, int, int]:
    if extended:
        visible = min(8, max(1, sample_count))
        columns = min(4, visible)
        return columns, math.ceil(visible / columns), visible
    return (2, 1, sample_count) if sample_count <= 2 else (2, 2, min(4, sample_count))


def locate_font(config: dict[str, Any]) -> Path | None:
    candidates = [
        os.environ.get("ATLAS_FONT_PATH"),
        config.get("font_path"),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    return next((Path(str(item)) for item in candidates if item and Path(str(item)).exists()), None)


def _font(path: Path | None, size: int) -> ImageFont.ImageFont:
    if path:
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap_pixels(draw: ImageDraw.ImageDraw, text: str, chosen_font: ImageFont.ImageFont, width: int, max_lines: int) -> list[str]:
    words = text.split() or ["Prompt", "text", "unavailable"]
    lines: list[str] = []
    current = ""
    while words and len(lines) < max_lines:
        word = words.pop(0)
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=chosen_font)[2] <= width:
            current = trial
        elif current:
            lines.append(current)
            current = word
        else:
            lines.append(word)
            current = ""
    if current and len(lines) < max_lines:
        lines.append(current)
    if words:
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return lines


def _contain(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (9, 20, 34))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def _sample_label(sample: Sample, role: str) -> tuple[str, str]:
    match = MEDIA_TAG_RE.match(sample.source_tag)
    date = match.group(1) if match else sample.source_tag
    dimensions = f"{sample.width}×{sample.height}" if sample.width and sample.height else "size unknown"
    seed = f"seed {sample.seed}" if sample.seed is not None else "seed unavailable"
    return role, f"{date} · {sample.run_id} · {dimensions} · {seed}"


def render_card(
    destination: Path,
    *,
    prompt_id: str,
    category: str,
    prompt: str,
    model: str,
    cohort_id: str,
    samples: Sequence[Sample],
    roles: Sequence[str],
    config: dict[str, Any],
    extended: bool = False,
) -> None:
    columns, rows, _ = grid_shape(len(samples), extended=extended)
    cell = int(config.get("cell_size", 960))
    gap = int(config.get("gap", 24))
    margin = int(config.get("margin", 48))
    header = int(config.get("header_height", 260))
    label_height = int(config.get("label_height", 82))
    width = margin * 2 + columns * cell + (columns - 1) * gap
    height = header + margin * 2 + rows * cell + (rows - 1) * gap

    canvas = Image.new("RGB", (width, height), (7, 16, 29))
    draw = ImageDraw.Draw(canvas)
    font_path = locate_font(config)
    title_font = _font(font_path, 48 if extended else 42)
    meta_font = _font(font_path, 24)
    prompt_font = _font(font_path, 32 if extended else 30)
    label_font = _font(font_path, 25)
    small_font = _font(font_path, 19)
    cyan, soft, white = (82, 211, 255), (156, 181, 204), (239, 248, 255)

    draw.text((margin, 32), f"{prompt_id} · {category}", font=title_font, fill=cyan)
    draw.text((margin, 88), f"{model} · cohort {cohort_id} · {len(samples)} displayed samples", font=meta_font, fill=soft)
    y = 130
    for line in _wrap_pixels(draw, prompt, prompt_font, width - margin * 2, int(config.get("prompt_max_lines", 3))):
        draw.text((margin, y), line, font=prompt_font, fill=white)
        y += 38

    for index in range(rows * columns):
        row, column = divmod(index, columns)
        x = margin + column * (cell + gap)
        y = header + row * (cell + gap)
        draw.rounded_rectangle((x, y, x + cell, y + cell), radius=22, fill=(13, 28, 47), outline=(49, 84, 112), width=2)
        if index >= len(samples):
            message = "Not enough historical samples"
            placeholder = _font(font_path, 32)
            box = draw.textbbox((0, 0), message, font=placeholder)
            draw.text((x + (cell - box[2]) / 2, y + (cell - box[3]) / 2), message, font=placeholder, fill=soft)
            continue
        sample = samples[index]
        with Image.open(Path(sample.extracted_path or "")) as source:
            fitted = _contain(source, (cell - 4, cell - label_height - 4))
        canvas.paste(fitted, (x + 2, y + 2))
        role, details = _sample_label(sample, roles[index] if index < len(roles) else f"Sample {index + 1}")
        label_y = y + cell - label_height
        draw.rectangle((x + 2, label_y, x + cell - 2, y + cell - 2), fill=(10, 23, 39))
        draw.text((x + 20, label_y + 10), role, font=label_font, fill=cyan if role == "Current" else white)
        draw.text((x + 20, label_y + 44), textwrap.shorten(details, width=95 if extended else 72, placeholder="…"), font=small_font, fill=soft)

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, "JPEG", quality=int(config.get("jpeg_quality", 90)), optimize=True, progressive=True)


def sample_public_dict(sample: Sample) -> dict[str, Any]:
    return {
        "source_tag": sample.source_tag,
        "run_id": sample.run_id,
        "timestamp": sample.timestamp,
        "finished_at": sample.finished_at,
        "seed": sample.seed,
        "settings": sample.settings,
        "archive_name": sample.archive_name,
        "archive_member": sample.archive_member,
        "sha256": sample.sha256,
        "width": sample.width,
        "height": sample.height,
    }
