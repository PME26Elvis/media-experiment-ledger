"""Video collection, verification, rendering, and packaging inputs for Prompt Repeatability Atlas."""
from __future__ import annotations

import json
import math
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

from prompt_atlas_core import locate_font, normalized_settings, stable_hash, temporal_quantiles
from prompt_atlas_data import command, read_jsonl, sha256_file

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
VIDEO_EVENT = "video_completed"


@dataclass
class VideoSample:
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
    duration_seconds: float | None = None
    average_frame_rate: float | None = None
    codec: str | None = None
    pixel_format: str | None = None
    container: str | None = None
    has_audio: bool = False

    @property
    def media_type(self) -> str:
        return "video"

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        return (
            self.finished_at or self.timestamp or self.release_published_at,
            self.source_tag,
            self.run_id,
            self.local_path or "",
        )


@dataclass
class VideoAtlasEntry:
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
    full_files: list[str] = field(default_factory=list)
    bundle_file: str | None = None
    media_type: str = "video"


def video_cohort_identity(prompt_id: str, model: str, settings: dict[str, Any]) -> str:
    return stable_hash(
        {
            "media_type": "video",
            "prompt_id": prompt_id,
            "model": model,
            "settings": settings,
        }
    )


def video_member_matches(member: str, prompt_id: str) -> bool:
    path = PurePosixPath(member)
    stem = path.stem
    return (
        path.suffix.lower() in VIDEO_SUFFIXES
        and "videos" in path.parts
        and (stem == prompt_id or stem.startswith(prompt_id + "_"))
    )


def collect_video_samples(
    rows: Sequence[dict[str, Any]],
    roots: dict[str, Path],
) -> list[VideoSample]:
    published = {
        str(row["tagName"]): str(row.get("publishedAt") or "")
        for row in rows
    }
    output: list[VideoSample] = []
    for tag, root in roots.items():
        for path in sorted(root.glob("run_*-outputs.jsonl")):
            run_id = path.name.removesuffix("-outputs.jsonl")
            for record in read_jsonl(path):
                if record.get("event") != VIDEO_EVENT or not record.get("prompt_id"):
                    continue
                payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
                prompt_id = str(record["prompt_id"])
                model = str(payload.get("model") or "unknown-model")
                settings = normalized_settings(payload)
                # Seed remains evidence on each sample, but is excluded from cohort identity.
                # The harvester intentionally draws a new random seed for every run; keeping
                # it in the cohort key would make every real video a singleton.
                settings.pop("seed", None)
                output.append(
                    VideoSample(
                        prompt_id=prompt_id,
                        category=str(record.get("category") or "uncategorized"),
                        prompt=str(payload.get("prompt") or ""),
                        model=model,
                        settings=settings,
                        cohort_id=video_cohort_identity(prompt_id, model, settings),
                        source_tag=tag,
                        release_published_at=published.get(tag, ""),
                        run_id=run_id,
                        timestamp=str(record.get("timestamp") or ""),
                        finished_at=str(record.get("finished_at") or ""),
                        local_path=str(record.get("local_path")) if record.get("local_path") else None,
                        seed=record.get("seed") if record.get("seed") is not None else payload.get("seed"),
                    )
                )
    return sorted(output, key=lambda item: item.sort_key)


def group_video_candidates(samples: Sequence[VideoSample]) -> dict[str, list[VideoSample]]:
    groups: dict[str, list[VideoSample]] = {}
    for sample in samples:
        groups.setdefault(sample.cohort_id, []).append(sample)
    return {
        key: sorted(value, key=lambda item: item.sort_key)
        for key, value in groups.items()
        if len(value) >= 2
    }


def download_video_archives(
    groups: dict[str, list[VideoSample]],
    root: Path,
) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    tags = sorted({sample.source_tag for group in groups.values() for sample in group})
    for tag in tags:
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        command(
            [
                "gh", "release", "download", tag,
                "--pattern", "run_*-videos*.zip",
                "--dir", str(target),
            ],
            check=False,
        )
        roots[tag] = target
    return roots


def _fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else None
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def probe_video(path: Path) -> dict[str, Any]:
    result = command(
        [
            "ffprobe", "-v", "error",
            "-show_streams", "-show_format",
            "-of", "json", str(path),
        ]
    )
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not isinstance(video_stream, dict):
        raise ValueError(f"No decodable video stream in {path}")
    format_row = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = _fraction(str(video_stream.get("duration") or format_row.get("duration") or ""))
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    if not duration or duration <= 0 or width <= 0 or height <= 0:
        raise ValueError(f"Incomplete video dimensions/duration for {path}")
    rate = _fraction(str(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or ""))
    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "average_frame_rate": rate,
        "codec": str(video_stream.get("codec_name") or "unknown"),
        "pixel_format": str(video_stream.get("pix_fmt") or "unknown"),
        "container": str(format_row.get("format_name") or path.suffix.lstrip(".")),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
    }


def validate_video(path: Path) -> dict[str, Any]:
    metadata = probe_video(path)
    duration = float(metadata["duration_seconds"])
    positions = sorted({
        0.0,
        max(0.0, duration * 0.5),
        max(0.0, duration - min(0.15, duration / 4)),
    })
    for position in positions:
        command(
            [
                "ffmpeg", "-v", "error", "-ss", f"{position:.3f}",
                "-i", str(path), "-frames:v", "1", "-f", "null", "-",
            ]
        )
    return metadata


def extract_videos(
    groups: dict[str, list[VideoSample]],
    archive_roots: dict[str, Path],
    extract_root: Path,
) -> None:
    needed: dict[tuple[str, str], set[str]] = {}
    index: dict[tuple[str, str, str], list[VideoSample]] = {}
    for group in groups.values():
        for sample in group:
            needed.setdefault((sample.source_tag, sample.run_id), set()).add(sample.prompt_id)
            index.setdefault((sample.source_tag, sample.run_id, sample.prompt_id), []).append(sample)

    for tag, root in archive_roots.items():
        for archive_path in sorted(root.glob("run_*-videos*.zip")):
            run_id = archive_path.name.split("-videos", 1)[0] if "-videos" in archive_path.name else None
            if not run_id or (tag, run_id) not in needed:
                continue
            try:
                archive = zipfile.ZipFile(archive_path)
            except zipfile.BadZipFile:
                continue
            with archive:
                for member in archive.namelist():
                    prompt_id = next(
                        (pid for pid in needed[(tag, run_id)] if video_member_matches(member, pid)),
                        None,
                    )
                    if not prompt_id:
                        continue
                    destination = extract_root / tag / run_id / PurePosixPath(member).name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    try:
                        metadata = validate_video(destination)
                    except Exception:
                        destination.unlink(missing_ok=True)
                        continue
                    digest = sha256_file(destination)
                    for sample in index.get((tag, run_id, prompt_id), []):
                        sample.archive_name = archive_path.name
                        sample.archive_member = member
                        sample.extracted_path = str(destination)
                        sample.sha256 = digest
                        for key, value in metadata.items():
                            setattr(sample, key, value)


def deduplicate_video_samples(
    samples: Sequence[VideoSample],
    preferred_tag: str | None = None,
) -> list[VideoSample]:
    groups: dict[str, list[VideoSample]] = {}
    for sample in sorted(samples, key=lambda item: item.sort_key):
        if sample.extracted_path and sample.sha256:
            groups.setdefault(sample.sha256, []).append(sample)
    output: list[VideoSample] = []
    for candidates in groups.values():
        preferred = [item for item in candidates if preferred_tag and item.source_tag == preferred_tag]
        output.append((preferred or candidates)[-1 if preferred else 0])
    return sorted(output, key=lambda item: item.sort_key)


def select_video_primary(samples: Sequence[VideoSample]) -> list[VideoSample]:
    ordered = sorted(samples, key=lambda item: item.sort_key)
    if len(ordered) <= 3:
        return ordered
    current = ordered[-1]
    selected = temporal_quantiles(ordered[:-1], min(3, len(ordered) - 1)) + [current]
    unique: list[VideoSample] = []
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


def video_roles(samples: Sequence[VideoSample]) -> list[str]:
    if len(samples) == 2:
        return ["Historical", "Latest"]
    if len(samples) == 3:
        return ["Earliest", "Historical", "Latest"]
    return ["Earliest", "Mid-history", "Latest prior", "Latest"]


def _font(path: Path | None, size: int) -> ImageFont.ImageFont:
    if path:
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _contain(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (9, 20, 34))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def normalize_video_gif(
    source: Path,
    destination: Path,
    *,
    width: int,
    height: int,
    fps: int,
    duration: float,
    colors: int,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    filter_graph = (
        f"[0:v]setpts=PTS-STARTPTS,fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x091422,"
        f"tpad=stop_mode=clone:stop_duration={duration:.3f},"
        f"trim=duration={duration:.3f},split[s0][s1];"
        f"[s0]palettegen=max_colors={colors}:stats_mode=diff[p];"
        f"[s1][p]paletteuse=dither=sierra2_4a"
    )
    command(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(source),
            "-filter_complex", filter_graph,
            "-loop", "0", str(destination),
        ]
    )


def _gif_frames(path: Path) -> list[Image.Image]:
    with Image.open(path) as image:
        return [frame.convert("RGB").copy() for frame in ImageSequence.Iterator(image)]


def _grid(count: int, extended: bool = False) -> tuple[int, int]:
    if extended:
        columns = min(4, max(1, count))
        return columns, math.ceil(count / columns)
    return (2, 1) if count <= 2 else (2, 2)


def render_video_gif(
    destination: Path,
    *,
    prompt_id: str,
    category: str,
    prompt: str,
    model: str,
    cohort_id: str,
    samples: Sequence[VideoSample],
    roles: Sequence[str],
    config: dict[str, Any],
    extended: bool = False,
) -> None:
    fps = max(1, int(config.get("video_preview_fps", 6)))
    duration = max(1.0, float(config.get("video_preview_seconds", 6)))
    colors = min(256, max(32, int(config.get("video_gif_colors", 128))))
    cell_width = int(
        config.get("video_extended_cell_width", 320)
        if extended
        else config.get("video_cell_width", 480)
    )
    cell_height = int(
        config.get("video_extended_cell_height", 180)
        if extended
        else config.get("video_cell_height", 270)
    )
    label_height = int(config.get("video_label_height", 58))
    margin = int(config.get("video_margin", 24))
    gap = int(config.get("video_gap", 16))
    header = int(config.get("video_header_height", 150))
    columns, rows = _grid(len(samples), extended=extended)
    width = margin * 2 + columns * cell_width + (columns - 1) * gap
    height = header + margin * 2 + rows * (cell_height + label_height) + (rows - 1) * gap
    font_path = locate_font(config)
    title_font = _font(font_path, 28 if extended else 32)
    meta_font = _font(font_path, 16 if extended else 18)
    label_font = _font(font_path, 16 if extended else 18)
    small_font = _font(font_path, 12 if extended else 14)

    with tempfile.TemporaryDirectory(prefix="video-atlas-gif-") as temp:
        temp_root = Path(temp)
        source_frames: list[list[Image.Image]] = []
        for index, sample in enumerate(samples):
            normalized = temp_root / f"{index:02d}.gif"
            normalize_video_gif(
                Path(sample.extracted_path or ""),
                normalized,
                width=cell_width,
                height=cell_height,
                fps=fps,
                duration=duration,
                colors=colors,
            )
            source_frames.append(_gif_frames(normalized))

        frame_count = max(1, int(round(duration * fps)))
        frames: list[Image.Image] = []
        for frame_index in range(frame_count):
            canvas = Image.new("RGB", (width, height), (7, 16, 29))
            draw = ImageDraw.Draw(canvas)
            draw.text(
                (margin, 20),
                f"{prompt_id} · {category} · VIDEO",
                font=title_font,
                fill=(82, 211, 255),
            )
            draw.text(
                (margin, 62),
                f"{model} · cohort {cohort_id} · {len(samples)} displayed samples",
                font=meta_font,
                fill=(156, 181, 204),
            )
            draw.text((margin, 92), prompt[:180], font=meta_font, fill=(239, 248, 255))
            for index in range(rows * columns):
                row, column = divmod(index, columns)
                x = margin + column * (cell_width + gap)
                y = header + margin + row * (cell_height + label_height + gap)
                if index >= len(samples):
                    draw.rounded_rectangle(
                        (x, y, x + cell_width, y + cell_height + label_height),
                        radius=14,
                        fill=(13, 28, 47),
                        outline=(49, 84, 112),
                        width=2,
                    )
                    draw.text(
                        (x + 24, y + cell_height // 2),
                        "Not enough historical samples",
                        font=label_font,
                        fill=(156, 181, 204),
                    )
                    continue
                sample = samples[index]
                frames_for_sample = source_frames[index]
                image = frames_for_sample[min(frame_index, len(frames_for_sample) - 1)]
                canvas.paste(image, (x, y))
                draw.rectangle(
                    (x, y + cell_height, x + cell_width, y + cell_height + label_height),
                    fill=(10, 23, 39),
                )
                role = roles[index] if index < len(roles) else f"Sample {index + 1}"
                detail = (
                    f"{sample.source_tag} · {sample.run_id} · "
                    f"{sample.width}×{sample.height} · {sample.duration_seconds:.2f}s"
                )
                draw.text(
                    (x + 12, y + cell_height + 8),
                    role,
                    font=label_font,
                    fill=(82, 211, 255) if role == "Latest" else (239, 248, 255),
                )
                draw.text(
                    (x + 12, y + cell_height + 32),
                    detail[:92],
                    font=small_font,
                    fill=(156, 181, 204),
                )
            frames.append(
                canvas.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors)
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            destination,
            save_all=True,
            append_images=frames[1:],
            duration=round(1000 / fps),
            loop=0,
            optimize=False,
            disposal=2,
        )


def extract_frame(path: Path, destination: Path, position: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, position):.3f}",
            "-i", str(path), "-frames:v", "1", "-q:v", "2", str(destination),
        ]
    )


def render_keyframe_pages(
    output_root: Path,
    prompt_id: str,
    category: str,
    model: str,
    cohort_id: str,
    samples: Sequence[VideoSample],
    page_size: int,
    config: dict[str, Any],
) -> list[str]:
    page_size = max(2, page_size)
    pages = [
        list(samples[start : start + page_size])
        for start in range(0, len(samples), page_size)
    ]
    names: list[str] = []
    font_path = locate_font(config)
    title_font = _font(font_path, 30)
    label_font = _font(font_path, 16)
    cell_w, cell_h, label_h = 480, 270, 54
    columns = 4
    margin, gap, header = 28, 16, 100

    for page_index, page in enumerate(pages, 1):
        rows = math.ceil(len(page) / columns)
        canvas = Image.new(
            "RGB",
            (
                margin * 2 + columns * cell_w + (columns - 1) * gap,
                header + margin * 2 + rows * (cell_h + label_h) + (rows - 1) * gap,
            ),
            (7, 16, 29),
        )
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (margin, 24),
            f"{prompt_id} · VIDEO KEYFRAMES · {model} · cohort {cohort_id}",
            font=title_font,
            fill=(82, 211, 255),
        )
        with tempfile.TemporaryDirectory(prefix="video-keyframes-") as temp:
            temp_root = Path(temp)
            for index, sample in enumerate(page):
                row, column = divmod(index, columns)
                x = margin + column * (cell_w + gap)
                y = header + margin + row * (cell_h + label_h + gap)
                duration = float(sample.duration_seconds or 0)
                positions = [duration * 0.1, duration * 0.5, duration * 0.9]
                strip = Image.new("RGB", (cell_w, cell_h), (9, 20, 34))
                segment_w = cell_w // 3
                for key_index, position in enumerate(positions):
                    frame_path = temp_root / f"{index}-{key_index}.jpg"
                    extract_frame(Path(sample.extracted_path or ""), frame_path, position)
                    with Image.open(frame_path) as source:
                        fitted = _contain(source, (segment_w, cell_h))
                    strip.paste(fitted, (key_index * segment_w, 0))
                canvas.paste(strip, (x, y))
                draw.rectangle(
                    (x, y + cell_h, x + cell_w, y + cell_h + label_h),
                    fill=(10, 23, 39),
                )
                draw.text(
                    (x + 10, y + cell_h + 8),
                    f"{sample.source_tag} · {sample.run_id}",
                    font=label_font,
                    fill=(239, 248, 255),
                )
                draw.text(
                    (x + 10, y + cell_h + 30),
                    f"{duration:.2f}s · {sample.width}×{sample.height} · {sample.codec}",
                    font=label_font,
                    fill=(156, 181, 204),
                )
        relative = (
            f"{prompt_id}-{cohort_id}/"
            f"page-{page_index:03d}-of-{len(pages):03d}-n{len(page)}.jpg"
        )
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(
            destination,
            "JPEG",
            quality=int(config.get("jpeg_quality", 90)),
            optimize=True,
            progressive=True,
        )
        names.append(relative)
    return names


def video_sample_public_dict(sample: VideoSample) -> dict[str, Any]:
    return {
        "media_type": "video",
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
        "duration_seconds": sample.duration_seconds,
        "average_frame_rate": sample.average_frame_rate,
        "codec": sample.codec,
        "pixel_format": sample.pixel_format,
        "container": sample.container,
        "has_audio": sample.has_audio,
    }


def build_video_entries(
    rows: Sequence[dict[str, Any]],
    metadata_roots: dict[str, Path],
    fingerprint: str,
    work: Path,
    output: Path,
    config: dict[str, Any],
    latest_tag: str,
    archive_roots: dict[str, Path] | None = None,
) -> tuple[list[VideoAtlasEntry], list[dict[str, Any]], int, int]:
    all_samples = collect_video_samples(rows, metadata_roots)
    groups = group_video_candidates(all_samples)
    resolved_archives = archive_roots or download_video_archives(
        groups,
        work / "video-archives",
    )
    extract_videos(groups, resolved_archives, work / "video-extracted")

    entries: list[VideoAtlasEntry] = []
    missing: list[dict[str, Any]] = []
    extended_max = max(5, int(config.get("video_extended_max_samples", 8)))
    full_page_size = max(2, int(config.get("video_full_page_samples", 16)))

    for cohort_id, raw in sorted(
        groups.items(),
        key=lambda item: (item[1][0].prompt_id, item[1][0].model, item[0]),
    ):
        samples = deduplicate_video_samples(raw, preferred_tag=latest_tag)
        if len(samples) < 2:
            missing.append(
                {
                    "media_type": "video",
                    "cohort_id": cohort_id,
                    "prompt_id": raw[0].prompt_id,
                    "metadata_samples": len(raw),
                    "usable_unique_media": len(samples),
                }
            )
            continue
        first = samples[0]
        primary = select_video_primary(samples)
        primary_name = f"video-atlas-{first.prompt_id}-{cohort_id}-n{len(primary)}.gif"
        render_video_gif(
            output / "video" / "primary" / primary_name,
            prompt_id=first.prompt_id,
            category=first.category,
            prompt=first.prompt,
            model=first.model,
            cohort_id=cohort_id,
            samples=primary,
            roles=video_roles(primary),
            config=config,
        )

        extended_name = None
        extended: list[VideoSample] = []
        if len(samples) >= int(config.get("video_extended_min_samples", 5)):
            extended = temporal_quantiles(samples, min(extended_max, len(samples)))
            extended_name = (
                f"video-atlas-{first.prompt_id}-{cohort_id}-"
                f"extended-n{len(extended)}.gif"
            )
            render_video_gif(
                output / "video" / "extended" / extended_name,
                prompt_id=first.prompt_id,
                category=first.category,
                prompt=first.prompt,
                model=first.model,
                cohort_id=cohort_id,
                samples=extended,
                roles=[
                    f"Temporal {index + 1}/{len(extended)}"
                    for index in range(len(extended))
                ],
                config=config,
                extended=True,
            )

        full_names = render_keyframe_pages(
            output / "video" / "keyframes",
            first.prompt_id,
            first.category,
            first.model,
            cohort_id,
            samples,
            full_page_size,
            config,
        )
        sidecar_name = f"video-atlas-{first.prompt_id}-{cohort_id}.json"
        sidecar = {
            "schema_version": 1,
            "media_type": "video",
            "dataset_scope": "all_published_media_exp_releases",
            "dataset_fingerprint": fingerprint,
            "latest_source_tag": latest_tag,
            "prompt_id": first.prompt_id,
            "category": first.category,
            "prompt": first.prompt,
            "model": first.model,
            "settings": first.settings,
            "cohort_id": cohort_id,
            "sample_count": len(samples),
            "selection_policy": {
                "primary": "earliest, temporal history anchors, latest cohort sample",
                "extended": f"up to {extended_max} temporal quantiles",
                "full": (
                    f"all unique videos paginated at {full_page_size} "
                    "per keyframe sheet"
                ),
                "deduplication": "exact SHA-256",
            },
            "rendering": {
                "preview_format": "GIF",
                "preview_seconds": config.get("video_preview_seconds", 6),
                "preview_fps": config.get("video_preview_fps", 6),
                "fit": "contain/letterbox",
                "keyframes": [0.1, 0.5, 0.9],
            },
            "all_samples": [video_sample_public_dict(item) for item in samples],
            "primary_samples": [video_sample_public_dict(item) for item in primary],
            "extended_samples": [video_sample_public_dict(item) for item in extended],
            "full_files": full_names,
        }
        sidecar_path = output / "video" / "sidecars" / sidecar_name
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        entries.append(
            VideoAtlasEntry(
                first.prompt_id,
                first.category,
                first.prompt,
                first.model,
                cohort_id,
                len(samples),
                latest_tag,
                primary_name,
                sidecar_name,
                extended_name,
                [video_sample_public_dict(item) for item in primary],
                [video_sample_public_dict(item) for item in extended],
                full_names,
            )
        )
    return entries, missing, len(all_samples), len(groups)
