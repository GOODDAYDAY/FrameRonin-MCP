"""
Phase 2 — Image processing tools.

- image_remove_gemini_watermark: Remove Gemini-generated image watermark
- image_resize: Scale image to specified dimensions
- image_crop: Crop image to rectangle
"""

from pathlib import Path
from PIL import Image

from ..lib.image_utils import load_image, save_image, resize_image, crop_image
from ..lib.watermark import remove_gemini_watermark


def handle_image_remove_gemini_watermark(args: dict) -> dict:
    """
    Remove the visible watermark from Gemini-generated images.
    Uses reverse alpha blending with embedded alpha mask.

    Required: image_path (str)
    Optional: output_path (str)
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)
    result = remove_gemini_watermark(img)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_clean.png")))
    save_image(result, output_path, "PNG")

    return {"output_path": str(output_path), "format": "PNG"}


def handle_image_resize(args: dict) -> dict:
    """
    Resize image to specified dimensions or scale factor.

    Required: image_path (str)
    Optional: output_path, width, height, scale (multiplier),
              method ("lanczos"|"nearest"|"bilinear", default "lanczos")
    Provide: (width, height), (width only), (height only), or (scale only).
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)
    orig_w, orig_h = img.size

    method_map = {
        "lanczos": Image.Resampling.LANCZOS,
        "nearest": Image.Resampling.NEAREST,
        "bilinear": Image.Resampling.BILINEAR,
        "bicubic": Image.Resampling.BICUBIC,
    }
    method = method_map.get(args.get("method", "lanczos"), Image.Resampling.LANCZOS)

    width = args.get("width")
    height = args.get("height")
    scale = args.get("scale")

    if width is not None:
        width = int(width)
    if height is not None:
        height = int(height)
    if scale is not None:
        scale = float(scale)

    if width is None and height is None and scale is None:
        return {"error": "Specify width, height, and/or scale"}

    result = resize_image(img, width=width, height=height, scale=scale, resample=method)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_resized.png")))
    save_image(result, output_path, "PNG")

    new_w, new_h = result.size
    return {
        "output_path": str(output_path),
        "original_size": {"width": orig_w, "height": orig_h},
        "new_size": {"width": new_w, "height": new_h},
    }


def handle_image_crop(args: dict) -> dict:
    """
    Crop image to a specified rectangle.

    Required: image_path (str)
    Optional: output_path, x (0), y (0), width, height
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)
    orig_w, orig_h = img.size

    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    width = int(args["width"]) if "width" in args else None
    height = int(args["height"]) if "height" in args else None

    result = crop_image(img, x, y, width, height)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_cropped.png")))
    save_image(result, output_path, "PNG")

    new_w, new_h = result.size
    return {
        "output_path": str(output_path),
        "original_size": {"width": orig_w, "height": orig_h},
        "crop_rect": {"x": x, "y": y, "width": new_w, "height": new_h},
    }


def handle_image_merge_grid(args: dict) -> dict:
    """
    Merge multiple images into a single sprite/atlas arranged in a grid.

    Required: image_paths (list[str]), columns (int)
    Optional: output_path, cell_w, cell_h, spacing (0)
    """
    paths = [Path(p) for p in args["image_paths"]]
    for p in paths:
        if not p.exists():
            return {"error": f"Image not found: {p}"}

    columns = int(args["columns"])
    images = [load_image(p) for p in paths]
    cell_w = int(args.get("cell_w", max(img.width for img in images)))
    cell_h = int(args.get("cell_h", max(img.height for img in images)))
    spacing = int(args.get("spacing", 0))

    rows = (len(images) + columns - 1) // columns
    sheet_w = columns * (cell_w + spacing) - spacing
    sheet_h = rows * (cell_h + spacing) - spacing

    sheet = Image.new("RGBA", (max(1, sheet_w), max(1, sheet_h)), (0, 0, 0, 0))
    for i, img in enumerate(images):
        col, row = i % columns, i // columns
        x = col * (cell_w + spacing) + (cell_w - img.width) // 2
        y = row * (cell_h + spacing) + (cell_h - img.height) // 2
        sheet.paste(img, (x, y), img if img.mode == "RGBA" else None)

    output_path = Path(args.get("output_path", str(paths[0].parent / "merged_grid.png")))
    save_image(sheet, output_path, "PNG")

    return {
        "output_path": str(output_path),
        "grid": {"columns": columns, "rows": rows, "total": len(images)},
        "sheet_size": {"width": sheet_w, "height": sheet_h},
    }
