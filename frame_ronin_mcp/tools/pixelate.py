"""
Phase 3 — Pixel art conversion tools.

- image_pixelate: Full proper-pixel-art pipeline with mesh detection
- image_pixelate_simple: Simple uniform-grid pixelation
"""

from pathlib import Path
from ..lib.image_utils import load_image, save_image
from ..lib.pixelate_core import process_pixelate, simple_pixelate


def handle_image_pixelate(args: dict) -> dict:
    """
    Convert image to pixel art using proper-pixel-art algorithm.

    Uses OpenCV to detect the original pixel grid (Canny + HoughLinesP),
    then downsamples each grid cell to its most common color.

    Required: image_path (str)
    Optional: output_path, upscale (1-7, default 1),
              num_colors (null = no quantization),
              scale_result (1-5, default 1),
              transparent_background (default false)
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)

    upscale = int(args.get("upscale", 1))
    scale_result = int(args.get("scale_result", 1))
    transparent_bg = bool(args.get("transparent_background", False))

    num_colors = args.get("num_colors")
    if num_colors is not None:
        num_colors = int(num_colors)

    result = process_pixelate(
        img,
        upscale=upscale,
        num_colors=num_colors,
        scale_result=scale_result,
        transparent_background=transparent_bg,
    )

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_pixel.png")))
    save_image(result, output_path, "PNG")

    return {
        "output_path": str(output_path),
        "output_size": {"width": result.width, "height": result.height},
        "method": "proper-pixel-art",
    }


def handle_image_pixelate_simple(args: dict) -> dict:
    """
    Convert image to pixel art using simple uniform grid (no mesh detection).

    Faster than image_pixelate — just divides image into pixel_size blocks
    and takes the median color of each.

    Required: image_path (str)
    Optional: output_path, pixel_size (default 8),
              num_colors (null = no quantization)
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)

    pixel_size = int(args.get("pixel_size", 8))

    num_colors = args.get("num_colors")
    if num_colors is not None:
        num_colors = int(num_colors)

    result = simple_pixelate(img, pixel_size=pixel_size, num_colors=num_colors)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_pixel.png")))
    save_image(result, output_path, "PNG")

    return {
        "output_path": str(output_path),
        "output_size": {"width": result.width, "height": result.height},
        "method": "simple-grid",
    }
