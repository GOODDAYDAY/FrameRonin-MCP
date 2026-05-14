"""
Phase 2 — GIF & Sprite Sheet tools.

- gif_extract_frames: Extract individual frames from GIF
- frames_to_gif: Combine image sequence into GIF
- spritesheet_split: Split sprite sheet by uniform grid
- spritesheet_compose: Compose frames into sprite sheet
"""

import math
from pathlib import Path
from PIL import Image


def handle_gif_extract_frames(args: dict) -> dict:
    """
    Extract individual frames from a GIF or animated image.

    Required: gif_path (str)
    Optional: output_dir, output_format ("png"|"jpg", default "png")

    Returns: list of frame file paths.
    """
    gif_path = Path(args["gif_path"])
    if not gif_path.exists():
        return {"error": f"GIF not found: {gif_path}"}

    output_dir = Path(args.get("output_dir", str(gif_path.parent / f"{gif_path.stem}_frames")))
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.get("output_format", "png").lower()

    img = Image.open(gif_path)
    frames: list[str] = []
    i = 0

    while True:
        frame_path = output_dir / f"frame_{i:05d}.{fmt}"
        frame = img.copy().convert("RGBA")
        frame.save(frame_path, format="PNG" if fmt == "png" else "JPEG")
        frames.append(str(frame_path))
        i += 1
        try:
            img.seek(i)
        except EOFError:
            break

    return {
        "frame_count": len(frames),
        "output_dir": str(output_dir),
        "frames": frames,
    }


def handle_frames_to_gif(args: dict) -> dict:
    """
    Combine a sequence of images into an animated GIF.

    Required: frame_paths (list[str])
    Optional: output_path, duration (ms per frame, default 100), loop (default 0=infinite)
    """
    paths = [Path(p) for p in args["frame_paths"]]
    for p in paths:
        if not p.exists():
            return {"error": f"Frame not found: {p}"}

    duration = int(args.get("duration", 100))
    loop = int(args.get("loop", 0))

    frames = []
    for p in paths:
        img = Image.open(p).convert("RGBA")
        # Composite over white for GIF compatibility
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        frames.append(bg.convert("P", palette=Image.Palette.ADAPTIVE))

    output_path = Path(args.get("output_path", str(paths[0].parent / "output.gif")))
    frames[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=loop,
        disposal=2,
    )

    return {
        "output_path": str(output_path),
        "frame_count": len(frames),
        "duration_ms": duration,
    }


def handle_spritesheet_split(args: dict) -> dict:
    """
    Split a sprite sheet into individual frame images by uniform grid.

    Required: image_path (str), columns (int), rows (int)
    Optional: output_dir, margin_x (0), margin_y (0), spacing_x (0), spacing_y (0)

    Returns: list of frame file paths and positions.
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = Image.open(image_path).convert("RGBA")
    img_w, img_h = img.size

    columns = int(args["columns"])
    rows = int(args["rows"])
    margin_x = int(args.get("margin_x", 0))
    margin_y = int(args.get("margin_y", 0))
    spacing_x = int(args.get("spacing_x", 0))
    spacing_y = int(args.get("spacing_y", 0))

    cell_w = (img_w - margin_x * 2 - spacing_x * (columns - 1)) // columns
    cell_h = (img_h - margin_y * 2 - spacing_y * (rows - 1)) // rows

    if cell_w <= 0 or cell_h <= 0:
        return {"error": f"Invalid grid: cell size ({cell_w}, {cell_h}) <= 0"}

    output_dir = Path(args.get("output_dir", str(image_path.parent / f"{image_path.stem}_split")))
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for row in range(rows):
        for col in range(columns):
            x = margin_x + col * (cell_w + spacing_x)
            y = margin_y + row * (cell_h + spacing_y)
            x = min(x, img_w - 1)
            y = min(y, img_h - 1)
            crop_w = min(cell_w, img_w - x)
            crop_h = min(cell_h, img_h - y)
            if crop_w <= 0 or crop_h <= 0:
                continue

            frame = img.crop((x, y, x + crop_w, y + crop_h))
            frame_path = output_dir / f"frame_r{row:03d}_c{col:03d}.png"
            frame.save(frame_path, "PNG")
            frames.append({
                "path": str(frame_path),
                "row": row, "col": col,
                "x": x, "y": y,
                "width": crop_w, "height": crop_h,
            })

    return {
        "output_dir": str(output_dir),
        "frame_count": len(frames),
        "cell_size": {"width": cell_w, "height": cell_h},
        "frames": frames,
    }


def handle_spritesheet_compose(args: dict) -> dict:
    """
    Compose individual frame images into a single sprite sheet.

    Required: frame_paths (list[str])
    Optional: output_path, columns (auto-square), cell_w, cell_h,
              spacing (0), bg_color ("transparent"|"#RRGGBB")
    """
    paths = [Path(p) for p in args["frame_paths"]]
    for p in paths:
        if not p.exists():
            return {"error": f"Frame not found: {p}"}

    frames: list[Image.Image] = [Image.open(p).convert("RGBA") for p in paths]

    frame_w = int(args.get("cell_w", max(f.width for f in frames)))
    frame_h = int(args.get("cell_h", max(f.height for f in frames)))
    spacing = int(args.get("spacing", 0))

    columns = args.get("columns")
    if columns is not None:
        columns = int(columns)
    else:
        columns = max(1, math.ceil(math.sqrt(len(frames))))

    rows = math.ceil(len(frames) / columns)
    sheet_w = columns * (frame_w + spacing) - spacing
    sheet_h = rows * (frame_h + spacing) - spacing

    bg_color = args.get("bg_color", "transparent")
    if bg_color == "transparent":
        sheet = Image.new("RGBA", (max(1, sheet_w), max(1, sheet_h)), (0, 0, 0, 0))
    else:
        bg_color = bg_color.lstrip("#")
        r, g, b = int(bg_color[0:2], 16), int(bg_color[2:4], 16), int(bg_color[4:6], 16)
        sheet = Image.new("RGBA", (max(1, sheet_w), max(1, sheet_h)), (r, g, b, 255))

    frames_index = []
    for i, frame in enumerate(frames):
        col = i % columns
        row = i // columns
        x = col * (frame_w + spacing) + (frame_w - frame.width) // 2
        y = row * (frame_h + spacing) + (frame_h - frame.height) // 2
        sheet.paste(frame, (x, y), frame)
        frames_index.append({
            "i": i, "col": col, "row": row,
            "x": x, "y": y,
            "w": frame_w, "h": frame_h,
        })

    output_path = Path(args.get("output_path", str(paths[0].parent / "spritesheet.png")))
    sheet.save(output_path, "PNG")

    return {
        "output_path": str(output_path),
        "frame_count": len(frames),
        "sheet_size": {"width": sheet_w, "height": sheet_h},
        "grid": {"columns": columns, "rows": rows},
        "frames": frames_index,
    }
