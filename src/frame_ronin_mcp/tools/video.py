"""
Phase 1 — Video processing tools.

- video_to_spritesheet: Extract frames, remove background, compose sprite sheet
- video_get_info: Probe video metadata
- video_remove_watermark: Remove Seedance/Jiemeng watermark
"""

import json
import math
import subprocess
import uuid
from pathlib import Path
from PIL import Image
import numpy as np

from ..lib.image_utils import save_image


def _get_video_info(video_path: Path) -> dict:
    """Probe video with ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    duration = 0
    width, height, fps = 0, 0, 30

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            if "r_frame_rate" in stream:
                num, den = map(int, stream["r_frame_rate"].split("/"))
                fps = num / den if den else 30
            break

    try:
        duration = float(data.get("format", {}).get("duration", 0))
    except (ValueError, KeyError, TypeError):
        duration = 0

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": int(duration * fps) if duration and fps else 0,
    }


def _extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: int,
    start_sec: float,
    end_sec: float | None,
    max_frames: int,
) -> list[tuple[Path, float]]:
    """Extract frames from video as PNG sequence via FFmpeg."""
    info = _get_video_info(video_path)
    duration = info["duration"]
    if end_sec is None or end_sec <= 0:
        end_sec = duration

    start_sec = max(0, min(start_sec, duration))
    end_sec = max(start_sec, min(end_sec, duration))

    output_dir.mkdir(parents=True, exist_ok=True)

    interval = 1.0 / fps
    timestamps: list[float] = []
    t = start_sec
    while t < end_sec and len(timestamps) < max_frames:
        timestamps.append(t)
        t += interval

    frames: list[tuple[Path, float]] = []
    for i, ts in enumerate(timestamps):
        out_path = output_dir / f"frame_{i:05d}.png"
        cmd = [
            "ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path),
            "-vframes", "1", "-f", "image2", str(out_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        frames.append((out_path, timestamps[i]))

    return frames


def _remove_background_rembg(input_path: Path, output_path: Path) -> None:
    """Remove background using rembg."""
    from rembg import remove, new_session
    session = new_session("u2net")
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=session)
    with open(output_path, "wb") as f:
        f.write(result)


def _compose_sprite_sheet(
    frames: list[Path],
    timestamps: list[float],
    frame_w: int,
    frame_h: int,
    spacing: int,
    columns: int,
    output_path: Path,
) -> dict:
    """Compose frames into sprite sheet, generate index JSON."""
    n = len(frames)
    cols = min(columns, n) if columns else max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols) if n else 0
    sheet_w = cols * (frame_w + spacing) - spacing
    sheet_h = rows * (frame_h + spacing) - spacing

    sheet = Image.new("RGBA", (max(1, sheet_w), max(1, sheet_h)), (0, 0, 0, 0))
    frames_index = []

    for i, (fp, t) in enumerate(zip(frames, timestamps)):
        img = Image.open(fp).convert("RGBA")
        img = img.resize((frame_w, frame_h), Image.Resampling.LANCZOS)
        col, row = i % cols, i // cols
        x, y = col * (frame_w + spacing), row * (frame_h + spacing)
        sheet.paste(img, (x, y), img)
        frames_index.append({
            "i": i, "x": x, "y": y,
            "w": frame_w, "h": frame_h,
            "t": round(t, 3),
        })

    sheet.save(output_path, "PNG")

    return {
        "version": "1.0",
        "frame_size": {"w": frame_w, "h": frame_h},
        "sheet_size": {"w": sheet_w, "h": sheet_h},
        "frame_count": n,
        "frames": frames_index,
    }


def handle_video_to_spritesheet(args: dict) -> dict:
    """
    Extract frames from video, remove background, compose sprite sheet.

    Required: video_path (str)
    Optional: output_dir, fps (default 12), target_w/target_h (256),
              start_sec (0), end_sec, max_frames (300),
              spacing (4), columns (12), remove_bg (true)
    """
    video_path = Path(args["video_path"])
    if not video_path.exists():
        return {"error": f"Video not found: {video_path}"}

    job_id = str(uuid.uuid4())[:12]
    output_dir = Path(args.get("output_dir", str(video_path.parent / "spritesheet_output")))
    output_dir.mkdir(parents=True, exist_ok=True)

    fps = int(args.get("fps", 12))
    start_sec = float(args.get("start_sec", 0))
    end_sec = args.get("end_sec")
    if end_sec is not None:
        end_sec = float(end_sec)
    max_frames = int(args.get("max_frames", 300))
    target_w = int(args.get("target_w", 256))
    target_h = int(args.get("target_h", 256))
    spacing = int(args.get("spacing", 4))
    columns = int(args.get("columns", 12))
    remove_bg = bool(args.get("remove_bg", True))

    temp_dir = output_dir / f"_temp_{job_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Extract
        frames_dir = temp_dir / "frames"
        extracted = _extract_frames(video_path, frames_dir, fps, start_sec, end_sec, max_frames)
        if not extracted:
            return {"error": "No frames extracted from video"}

        # Process
        processed_dir = temp_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed: list[Path] = []

        for i, (src, ts) in enumerate(extracted):
            dest = processed_dir / f"out_{i:05d}.png"
            if remove_bg:
                try:
                    _remove_background_rembg(src, dest)
                except Exception:
                    # Fallback: just resize
                    img = Image.open(src).convert("RGBA")
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    img.save(dest, "PNG")
            else:
                img = Image.open(src).convert("RGBA")
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                img.save(dest, "PNG")
            processed.append(dest)

        # Compose
        sprite_path = output_dir / "sprite.png"
        index_data = _compose_sprite_sheet(
            processed, [t for _, t in extracted],
            target_w, target_h, spacing, columns, sprite_path
        )

        index_path = output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        return {
            "sprite_path": str(sprite_path),
            "index_path": str(index_path),
            "frame_count": index_data["frame_count"],
            "sheet_size": index_data["sheet_size"],
        }
    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def handle_video_get_info(args: dict) -> dict:
    """Probe video file metadata."""
    video_path = Path(args["video_path"])
    if not video_path.exists():
        return {"error": f"Video not found: {video_path}"}
    return _get_video_info(video_path)


def handle_video_remove_watermark(args: dict) -> dict:
    """
    Remove Seedance/Jiemeng "AI生成" watermark from video.

    Required: video_path (str)
    Optional: output_path (str)
    """
    video_path = Path(args["video_path"])
    if not video_path.exists():
        return {"error": f"Video not found: {video_path}"}

    output_path = Path(args.get("output_path", str(video_path.parent / f"{video_path.stem}_clean.mp4")))

    # Crop bottom-right watermark region (standard Seedance watermark location)
    # Watermark is ~180px tall at bottom
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", "crop=iw:ih-180:0:0",
        "-c:a", "copy",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": f"FFmpeg failed: {result.stderr}"}

    return {
        "output_path": str(output_path),
        "method": "crop_bottom_180px",
    }
