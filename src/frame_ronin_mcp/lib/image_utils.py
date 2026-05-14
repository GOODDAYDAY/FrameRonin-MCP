"""Shared image utilities — load, save, convert, resize, crop."""

import io
import base64
from pathlib import Path
from PIL import Image


def load_image(source: str | bytes | Path) -> Image.Image:
    """Load image from file path, base64 string, or raw bytes. Returns RGBA PIL Image."""
    if isinstance(source, bytes):
        img = Image.open(io.BytesIO(source))
    elif isinstance(source, Path):
        img = Image.open(source)
    elif isinstance(source, str):
        if source.startswith("data:") and "," in source:
            source = source.split(",", 1)[1]
        try:
            raw = base64.b64decode(source)
            img = Image.open(io.BytesIO(raw))
        except Exception:
            if Path(source).exists():
                img = Image.open(source)
            else:
                raise ValueError(f"Cannot parse input: not a valid file path or base64")
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")
    return img.convert("RGBA")


def save_image(img: Image.Image, output_path: str | Path, format: str = "PNG") -> Path:
    """Save PIL image to file. Returns output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format=format)
    return output_path


def image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL image to bytes."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL image to base64 data URL."""
    b = image_to_bytes(img, format)
    return f"data:image/{format.lower()};base64,{base64.b64encode(b).decode()}"


def resize_image(
    img: Image.Image,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    resample: int = Image.Resampling.LANCZOS,
) -> Image.Image:
    """Resize image. Specify width/height, scale factor, or both dimensions."""
    w, h = img.size
    if scale is not None:
        w, h = int(w * scale), int(h * scale)
    if width is not None and height is not None:
        w, h = width, height
    elif width is not None:
        ratio = width / w
        w, h = width, int(h * ratio)
    elif height is not None:
        ratio = height / h
        w, h = int(w * ratio), height
    return img.resize((max(1, w), max(1, h)), resample)


def crop_image(
    img: Image.Image,
    x: int = 0,
    y: int = 0,
    width: int | None = None,
    height: int | None = None,
) -> Image.Image:
    """Crop image to specified rectangle."""
    w, h = img.size
    right = min(w, x + width) if width is not None else w
    lower = min(h, y + height) if height is not None else h
    return img.crop((max(0, x), max(0, y), right, lower))


def scale_nearest_neighbor(img: Image.Image, width: int, height: int) -> Image.Image:
    """Nearest-neighbor upscale (pixel-perfect)."""
    return img.resize((width, height), Image.Resampling.NEAREST)


def get_image_info(img: Image.Image) -> dict:
    """Return basic image metadata."""
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "has_alpha": img.mode in ("RGBA", "LA", "PA"),
    }
