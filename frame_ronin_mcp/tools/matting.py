"""
Phase 1+2 — Image matting / background removal tools.

- image_remove_background: AI matting via rembg (Phase 1)
- image_chroma_key: Green/blue screen matting (Phase 2)
- image_double_background_matte: Black+white differential matting (Phase 2)
"""

from pathlib import Path
from ..lib.image_utils import load_image, save_image
from ..lib.chroma_key import chroma_key
from ..lib.double_bg import (
    double_background_matte,
    post_process_double_bg_matte,
    erode_alpha_frontier,
)


def handle_image_remove_background(args: dict) -> dict:
    """
    AI-powered background removal using rembg (U2Net model).

    Required: image_path (str) — path to input image
    Optional: output_path (str) — path for result PNG

    First call downloads the model (~176MB), may be slow.
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    from rembg import remove, new_session
    session = new_session("u2net")
    with open(image_path, "rb") as f:
        data = f.read()
    result = remove(data, session=session)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_nobg.png")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(result)

    return {"output_path": str(output_path), "format": "PNG", "has_alpha": True}


def handle_image_chroma_key(args: dict) -> dict:
    """
    Remove green/blue screen background using chroma key.

    Required: image_path (str)
    Optional: output_path, key_color ("green"|"blue"|"#RRGGBB"),
              tolerance (0-100, default 35),
              smoothness (0-100, default 34),
              spill (0-100, default 75),
              erosion (0-100, default 0)
    """
    image_path = Path(args["image_path"])
    if not image_path.exists():
        return {"error": f"Image not found: {image_path}"}

    img = load_image(image_path)
    key = args.get("key_color", "green")

    if key == "green":
        key_rgb = (0, 255, 0)
    elif key == "blue":
        key_rgb = (0, 0, 255)
    elif isinstance(key, str) and key.startswith("#"):
        key = key.lstrip("#")
        key_rgb = (int(key[0:2], 16), int(key[2:4], 16), int(key[4:6], 16))
    elif isinstance(key, list) and len(key) == 3:
        key_rgb = tuple(key)  # type: ignore
    else:
        key_rgb = (0, 255, 0)

    tolerance = int(args.get("tolerance", 35))
    smoothness = int(args.get("smoothness", 34))
    spill = int(args.get("spill", 75))
    erosion = int(args.get("erosion", 0))
    erosion_passes = min(5, round((erosion / 100) * 10))

    result = chroma_key(img, key_rgb, tolerance, smoothness, spill, erosion_passes)

    output_path = Path(args.get("output_path", str(image_path.parent / f"{image_path.stem}_chroma.png")))
    save_image(result, output_path, "PNG")

    return {"output_path": str(output_path), "format": "PNG", "has_alpha": True}


def handle_image_double_background_matte(args: dict) -> dict:
    """
    Extract alpha from paired black/white background images.

    Required: black_image_path (str), white_image_path (str)
              Both must be the same subject shot on black and white backgrounds.
    Optional: output_path, tolerance (50-100, default 70),
              edge_contrast (50-100, default 53),
              post_process (bool, default False),
              erosion (0-100, default 0)
    """
    black_path = Path(args["black_image_path"])
    white_path = Path(args["white_image_path"])
    if not black_path.exists():
        return {"error": f"Black image not found: {black_path}"}
    if not white_path.exists():
        return {"error": f"White image not found: {white_path}"}

    black = load_image(black_path)
    white = load_image(white_path)

    tolerance = int(args.get("tolerance", 70))
    edge_contrast = int(args.get("edge_contrast", 53))

    result = double_background_matte(black, white, tolerance, edge_contrast)

    if args.get("post_process", False):
        result = post_process_double_bg_matte(result)

    erosion = int(args.get("erosion", 0))
    if erosion > 0:
        result = erode_alpha_frontier(result, erosion)

    output_path = Path(args.get("output_path", str(black_path.parent / f"{black_path.stem}_doublebg.png")))
    save_image(result, output_path, "PNG")

    return {"output_path": str(output_path), "format": "PNG", "has_alpha": True}
