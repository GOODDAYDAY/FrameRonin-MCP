"""
Double-background matting: black-bg vs white-bg differential alpha extraction.

Ported from FrameRonin frontend doubleBackgroundMatte.ts.
Algorithm: upload the same scene on both black and white backgrounds.
The difference reveals the alpha channel: diff = avg(white - black per channel)
alpha = 255 - diff * tolScale, then gamma-corrected.
"""

import numpy as np
from PIL import Image


def double_background_matte(
    black_img: Image.Image,
    white_img: Image.Image,
    tolerance: int = 70,
    edge_contrast: int = 53,
) -> Image.Image:
    """
    Extract alpha channel from paired black/white background images.

    Both images must have identical dimensions and show the same subject
    on pure black (#000) and pure white (#FFF) backgrounds respectively.

    Args:
        black_img: Image with black background.
        white_img: Image with white background.
        tolerance: 50-100, lower = more aggressive removal.
        edge_contrast: 50-100, gamma on alpha (higher = sharper edges).

    Returns:
        RGBA image with background removed.
    """
    black = black_img.convert("RGBA")
    white = white_img.convert("RGBA")

    if black.size != white.size:
        raise ValueError(
            f"Image dimensions must match: {black.size} vs {white.size}"
        )

    w, h = black.size
    black_arr = np.array(black, dtype=np.float32)
    white_arr = np.array(white, dtype=np.float32)

    tol_scale = 0.5 + tolerance / 100.0
    gamma = 0.5 + edge_contrast / 100.0

    diff = (
        (white_arr[:, :, 0] - black_arr[:, :, 0])
        + (white_arr[:, :, 1] - black_arr[:, :, 1])
        + (white_arr[:, :, 2] - black_arr[:, :, 2])
    ) / 3.0

    alpha_raw = np.maximum(0, np.minimum(255, 255.0 - diff * tol_scale))
    alpha = np.round(255.0 * np.power(alpha_raw / 255.0, gamma))

    result = np.zeros((h, w, 4), dtype=np.uint8)
    mask = alpha > 0
    for c in range(3):
        result[:, :, c] = np.where(
            mask,
            np.round((black_arr[:, :, c] * 255.0) / np.maximum(alpha, 1)).astype(np.uint8),
            0,
        )
    result[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)

    return Image.fromarray(result, "RGBA")


def post_process_double_bg_matte(img: Image.Image) -> Image.Image:
    """
    Post-process double-background matte result:
    - Composite 4x to boost alpha
    - Threshold alpha at 20%
    - Remove small alpha islands (<12-20px depending on image size)

    Returns cleaned RGBA image.
    """
    w, h = img.size
    arr = np.array(img.convert("RGBA"), dtype=np.uint8)

    # Composite 4x: multiply alpha (each pass squares effective density)
    alpha = arr[:, :, 3].astype(np.float32)
    for _ in range(4):
        alpha = alpha * (alpha / 255.0)
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)

    # Threshold
    alpha_min = int(255 * 0.2)
    mask = alpha < alpha_min
    alpha[mask] = 0
    arr[mask, 0:3] = 0
    arr[:, :, 3] = alpha

    # Remove small islands (connected component analysis)
    min_island = 20 if w * h > 2_000_000 else (16 if w * h > 800_000 else 12)
    arr = _remove_small_alpha_islands(arr, alpha_min, min_island)

    return Image.fromarray(arr, "RGBA")


def _remove_small_alpha_islands(
    arr: np.ndarray, alpha_threshold: int, min_area: int
) -> np.ndarray:
    """Remove 8-connected alpha regions smaller than min_area."""
    h, w = arr.shape[:2]
    solid = arr[:, :, 3] >= alpha_threshold
    visited = np.zeros((h, w), dtype=bool)
    result = arr.copy()

    for y in range(h):
        for x in range(w):
            if not solid[y, x] or visited[y, x]:
                continue
            # BFS to find connected component
            stack = [(y, x)]
            region = []
            while stack:
                cy, cx = stack.pop()
                if cy < 0 or cx < 0 or cy >= h or cx >= w:
                    continue
                if visited[cy, cx] or not solid[cy, cx]:
                    continue
                visited[cy, cx] = True
                region.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        stack.append((cy + dy, cx + dx))

            if len(region) < min_area:
                for cy, cx in region:
                    result[cy, cx, :] = 0

    return result


def erode_alpha_frontier(
    img: Image.Image, erosion_ui: int = 0
) -> Image.Image:
    """
    Apply alpha erosion to double-bg matte result.
    Shaves semi-transparent edges layer by layer (no blur).

    Args:
        img: RGBA image.
        erosion_ui: 0-100, maps to 0-56 passes of frontier erosion.

    Returns:
        RGBA image with eroded alpha edges.
    """
    arr = np.array(img.convert("RGBA"), dtype=np.int32)
    h, w = arr.shape[:2]

    max_passes = 56
    u = min(1.0, max(0.0, erosion_ui / 100.0))
    passes = min(max_passes, round(u * max_passes))

    if passes <= 0:
        return Image.fromarray(arr.astype(np.uint8), "RGBA")

    shave = 22
    bg_alpha = 10

    for _ in range(passes):
        frontier = np.zeros((h, w), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                a = arr[y, x, 3]
                if a <= bg_alpha:
                    continue
                if x == 0 or x == w - 1 or y == 0 or y == h - 1:
                    frontier[y, x] = 1
                else:
                    if (arr[y - 1, x, 3] <= bg_alpha
                        or arr[y + 1, x, 3] <= bg_alpha
                        or arr[y, x - 1, 3] <= bg_alpha
                        or arr[y, x + 1, 3] <= bg_alpha):
                        frontier[y, x] = 1

        for y in range(h):
            for x in range(w):
                if not frontier[y, x]:
                    continue
                a = arr[y, x, 3]
                if a <= 0:
                    continue
                na = max(0, a - shave)
                if na <= 0:
                    arr[y, x, :] = 0
                else:
                    scale = na / a
                    arr[y, x, 0] = round(arr[y, x, 0] * scale)
                    arr[y, x, 1] = round(arr[y, x, 1] * scale)
                    arr[y, x, 2] = round(arr[y, x, 2] * scale)
                    arr[y, x, 3] = na

    arr[arr[:, :, 3] == 0, 0:3] = 0
    return Image.fromarray(arr.astype(np.uint8), "RGBA")
