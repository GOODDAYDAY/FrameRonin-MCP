"""
Gemini watermark removal via reverse alpha blending.

Algorithm from: https://github.com/allenk/GeminiWatermarkTool
Formula: watermarked = alpha * logo + (1-alpha) * original
         => original = (watermarked - alpha * logo) / (1-alpha)

The 48x48 alpha mask is embedded as base64 PNG (from GeminiWatermarkTool/assets).
For 96px watermark, the 48px mask is bilinearly upscaled.
"""

import io
import base64
import math
from PIL import Image
import numpy as np

# Embedded alpha mask (48x48 grayscale PNG) from GeminiWatermarkTool
_BG_48_BASE64 = (
    "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"
)

# Constants from GeminiWatermarkTool
_LOGO_VALUE = 255  # Logo pixel value (white)
_ALPHA_THRESHOLD = 0.002
_MAX_ALPHA = 0.99


def _load_alpha_mask(size: int = 48) -> tuple[np.ndarray, int, int]:
    """Load embedded alpha mask as numpy array (0-1 float)."""
    raw = base64.b64decode(_BG_48_BASE64)
    img = Image.open(io.BytesIO(raw)).convert("L")
    arr = np.array(img, dtype=np.float32) / 255.0
    if size == 96:
        img96 = Image.fromarray((arr * 255).astype(np.uint8)).resize((96, 96), Image.BILINEAR)
        arr = np.array(img96, dtype=np.float32) / 255.0
    return arr


def _create_approx_alpha_map(size: int) -> np.ndarray:
    """Fallback: create approximate star-shaped alpha mask."""
    cx = cy = size / 2
    y, x = np.ogrid[:size, :size]
    dx = (x - cx) / cx
    dy = (y - cy) / cy
    r = np.sqrt(dx * dx + dy * dy)
    angle = np.arctan2(dy, dx)
    star = np.abs(np.sin(angle * 4)) * 0.5 + 0.5
    radial = np.maximum(0, 1 - r * (1.2 - star * 0.3))
    return np.minimum(1, radial * 0.6)


def get_watermark_params(img_width: int, img_height: int, size: int) -> dict:
    """Calculate watermark position (bottom-right corner)."""
    margin = 32 if size == 48 else 64
    return {
        "size": size,
        "margin": margin,
        "x": img_width - margin - size,
        "y": img_height - margin - size,
    }


def get_watermark_size(img_width: int, img_height: int) -> int:
    """Determine watermark size: 96 for large images (>1024), 48 otherwise."""
    return 96 if (img_width > 1024 and img_height > 1024) else 48


def remove_gemini_watermark(img: Image.Image) -> Image.Image:
    """
    Remove Gemini watermark from an image using reverse alpha blending.
    Returns new RGBA image with watermark removed.
    """
    w, h = img.size
    img = img.convert("RGBA")
    pixels = np.array(img, dtype=np.float32)

    base_size = get_watermark_size(w, h)
    params = get_watermark_params(w, h, base_size)

    try:
        alpha_map = _load_alpha_mask(base_size)
    except Exception:
        alpha_map = _create_approx_alpha_map(base_size)

    map_h, map_w = alpha_map.shape
    x, y = params["x"], params["y"]

    x1, y1 = max(0, x), max(0, y)
    x2 = min(w, x + map_w)
    y2 = min(h, y + map_h)

    for py in range(y1, y2):
        for px in range(x1, x2):
            alpha_idx_y = py - y
            alpha_idx_x = px - x
            if alpha_idx_y < 0 or alpha_idx_y >= map_h:
                continue
            if alpha_idx_x < 0 or alpha_idx_x >= map_w:
                continue

            alpha = min(alpha_map[alpha_idx_y, alpha_idx_x], _MAX_ALPHA)
            if alpha < _ALPHA_THRESHOLD:
                continue

            one_minus_alpha = 1.0 - alpha
            for c in range(3):
                watermarked = pixels[py, px, c]
                original = (watermarked - alpha * _LOGO_VALUE) / one_minus_alpha
                if original >= 0:
                    pixels[py, px, c] = max(0, min(255, round(original)))

    return Image.fromarray(pixels.astype(np.uint8), "RGBA")
