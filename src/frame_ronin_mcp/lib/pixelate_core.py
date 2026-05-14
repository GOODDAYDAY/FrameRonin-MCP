"""
Proper pixel art downsampling.

Ported from FrameRonin frontend lib/pixellise/pixelate.ts.
Algorithm from: https://github.com/KennethJAllen/proper-pixel-art

Pipeline:
  1. Quantize colors (k-means in RGB space)
  2. Mesh-based downsample: for each cell, pick most common opaque color
  3. Majority-transparent cells become transparent
  4. Optional nearest-neighbor output scaling
"""

import numpy as np
from PIL import Image

from .mesh import compute_mesh_with_scaling, HAS_OPENCV, Mesh

ALPHA_THRESHOLD = 128


def _make_background_transparent(arr: np.ndarray) -> np.ndarray:
    """Set white-ish pixels to transparent."""
    mask = (
        (arr[:, :, 0] > 250)
        & (arr[:, :, 1] > 250)
        & (arr[:, :, 2] > 250)
    )
    arr[mask, 3] = 0
    return arr


def _palette_quantize(arr: np.ndarray, num_colors: int) -> np.ndarray:
    """Quantize RGB colors using k-means clustering."""
    h, w = arr.shape[:2]
    rgb = arr[:, :, :3].reshape(-1, 3).astype(np.float32)

    # Simple median-cut style quantization (no sklearn dependency)
    # Use k-means via OpenCV if available
    if HAS_OPENCV:
        import cv2
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(rgb, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        centers = centers.astype(np.uint8)
        quantized = centers[labels.flatten()].reshape(h, w, 3)
    else:
        # Fallback: uniform quantization per channel
        bins = max(2, int(np.ceil(num_colors ** (1 / 3))))
        quantized = (rgb.reshape(h, w, 3).astype(np.float32) / 255.0 * (bins - 1))
        quantized = np.round(quantized) / (bins - 1) * 255.0
        quantized = quantized.astype(np.uint8)

    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = quantized
    result[:, :, 3] = arr[:, :, 3]
    return result


def _scale_nearest_alpha(alpha: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Nearest-neighbor scale alpha channel."""
    h, w = alpha.shape
    yy = (np.arange(target_h) * h / target_h).astype(np.int32)
    xx = (np.arange(target_w) * w / target_w).astype(np.int32)
    return alpha[yy[:, None], xx[None, :]]


def _scale_nearest_rgba(arr: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Nearest-neighbor scale RGBA array."""
    h, w = arr.shape[:2]
    yy = (np.arange(target_h) * h / target_h).astype(np.int32)
    xx = (np.arange(target_w) * w / target_w).astype(np.int32)
    return arr[yy[:, None], xx[None, :], :]


def _most_common_rgb(cell: np.ndarray) -> tuple[int, int, int]:
    """Find most common RGB color in a cell (opaque pixels only)."""
    opaque = cell[:, :, 3] >= ALPHA_THRESHOLD
    if not np.any(opaque):
        return (0, 0, 0)
    colors = cell[opaque, :3]
    # Hash colors to find most common
    hashes = colors[:, 0].astype(np.int64) * 65536 + colors[:, 1].astype(np.int64) * 256 + colors[:, 2].astype(np.int64)
    unique, counts = np.unique(hashes, return_counts=True)
    best_hash = unique[np.argmax(counts)]
    r = (best_hash // 65536)
    g = ((best_hash % 65536) // 256)
    b = (best_hash % 256)
    return (int(r), int(g), int(b))


def _is_majority_transparent(cell: np.ndarray) -> bool:
    """Check if more than half the cell pixels are transparent."""
    opaque = np.sum(cell[:, :, 3] >= ALPHA_THRESHOLD)
    total = cell.shape[0] * cell.shape[1]
    return opaque <= total / 2


def _downsample_proper(
    scaled_rgb: np.ndarray,
    scaled_alpha: np.ndarray,
    mesh: Mesh,
) -> np.ndarray:
    """Downsample image to pixel art using mesh grid."""
    vx, hy = mesh
    iw, ih = scaled_rgb.shape[1], scaled_rgb.shape[0]
    out_w, out_h = len(vx) - 1, len(hy) - 1
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)

    for j in range(out_h):
        y0, y1 = max(0, min(ih, hy[j])), max(0, min(ih, hy[j + 1]))
        for i in range(out_w):
            x0, x1 = max(0, min(iw, vx[i])), max(0, min(iw, vx[i + 1]))
            cell_pixels = (x1 - x0) * (y1 - y0)
            if cell_pixels <= 0:
                continue

            cell_rgb = scaled_rgb[y0:y1, x0:x1]
            cell_alpha = scaled_alpha[y0:y1, x0:x1]
            cell = np.zeros((y1 - y0, x1 - x0, 4), dtype=np.uint8)
            cell[:, :, :3] = cell_rgb
            cell[:, :, 3] = cell_alpha

            if _is_majority_transparent(cell):
                out[j, i, 3] = 0
            else:
                r, g, b = _most_common_rgb(cell)
                out[j, i, 0] = r
                out[j, i, 1] = g
                out[j, i, 2] = b
                out[j, i, 3] = 255

    return out


def process_pixelate(
    img: Image.Image,
    upscale: int = 1,
    num_colors: int | None = None,
    scale_result: int = 1,
    transparent_background: bool = False,
) -> Image.Image:
    """
    Convert image to pixel art using proper-pixel-art algorithm.

    Args:
        img: Input RGBA image.
        upscale: Nearest-neighbor scale before mesh detection (1-7).
        num_colors: Number of colors for quantization (None = no quantize).
        scale_result: Output scale factor per logical pixel (1-5).
        transparent_background: Make white-ish pixels transparent.

    Returns:
        Pixel art RGBA image.
    """
    arr = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = arr.shape[:2]

    # Mesh detection
    mesh, _, sw, sh = compute_mesh_with_scaling(arr, upscale)

    # Alpha scaling
    alpha = arr[:, :, 3]
    scaled_alpha = _scale_nearest_alpha(alpha, sw, sh)

    # Color quantization
    processed = arr
    if num_colors is not None and num_colors > 0:
        processed = _palette_quantize(processed, num_colors)

    # Scale RGB to detection size
    scaled_rgb = _scale_nearest_rgba(processed, sw, sh)[:, :, :3]

    # Proper downsample
    result = _downsample_proper(scaled_rgb, scaled_alpha, mesh)

    # Optional transparency
    if transparent_background:
        result = _make_background_transparent(result)

    # Output scaling
    sr = max(1, min(5, int(scale_result)))
    if sr > 1:
        rh, rw = result.shape[0] * sr, result.shape[1] * sr
        result = _scale_nearest_rgba(result, rw, rh)

    return Image.fromarray(result, "RGBA")


def simple_pixelate(
    img: Image.Image,
    pixel_size: int = 8,
    num_colors: int | None = None,
) -> Image.Image:
    """
    Simple uniform-grid pixel art conversion (no mesh detection).

    Args:
        img: Input RGBA image.
        pixel_size: Size of each output pixel block.
        num_colors: Number of colors for quantization.

    Returns:
        Pixel art RGBA image.
    """
    arr = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = arr.shape[:2]

    # Quantize
    if num_colors is not None and num_colors > 0:
        arr = _palette_quantize(arr, num_colors)

    ps = max(1, pixel_size)
    out_h, out_w = h // ps, w // ps
    result = np.zeros((out_h, out_w, 4), dtype=np.uint8)

    for y in range(out_h):
        for x in range(out_w):
            y0, y1 = y * ps, min(h, (y + 1) * ps)
            x0, x1 = x * ps, min(w, (x + 1) * ps)
            cell = arr[y0:y1, x0:x1]
            result[y, x, :3] = np.median(cell[:, :, :3], axis=(0, 1)).astype(np.uint8)
            result[y, x, 3] = 255

    return Image.fromarray(result, "RGBA")
