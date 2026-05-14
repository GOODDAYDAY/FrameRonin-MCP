"""
Chroma key (green/blue screen) matting.

Ported from FrameRonin frontend ImageMatte.tsx chromaKeyCanvas().
Uses Euclidean distance in RGB space with tolerance, smoothness, and spill suppression.
"""

import numpy as np
from PIL import Image


def chroma_key(
    img: Image.Image,
    key_color: tuple[int, int, int] = (0, 255, 0),
    tolerance: int = 35,
    smoothness: int = 34,
    spill: int = 75,
    erosion_passes: int = 0,
) -> Image.Image:
    """
    Remove green/blue screen background from image.

    Args:
        img: Input RGBA image.
        key_color: RGB tuple of the key color to remove (default green).
        tolerance: 0-100, how strictly to match key color.
        smoothness: 0-100, transition band width.
        spill: 0-100, color spill suppression strength.
        erosion_passes: Alpha erosion passes (0-10) to clean edges.

    Returns:
        RGBA image with background removed.
    """
    img = img.convert("RGBA")
    w, h = img.size
    pixels = np.array(img, dtype=np.float32)

    kr, kg, kb = key_color
    thresh = (tolerance / 100.0) * 100.0
    smooth = 50.0 + (smoothness / 100.0) * 120.0
    spill_str = spill / 100.0

    dr = pixels[:, :, 0] - kr
    dg = pixels[:, :, 1] - kg
    db = pixels[:, :, 2] - kb
    dist = np.sqrt(dr * dr + dg * dg + db * db)

    # Alpha calculation
    alpha = np.zeros((h, w), dtype=np.float32)
    mask_full = dist >= (thresh + smooth)
    mask_none = dist <= thresh
    mask_blend = ~mask_full & ~mask_none
    alpha[mask_full] = 1.0
    alpha[mask_blend] = (dist[mask_blend] - thresh) / smooth
    alpha = np.minimum(1.0, alpha)

    # Spill suppression
    if spill_str > 0 and np.any(alpha > 0):
        base_mask = np.maximum(0, dist - thresh)
        spill_val = np.power(np.minimum(1, base_mask / max(1, spill_str * 120)), 1.5)

        gray = (
            pixels[:, :, 0] * 0.2126
            + pixels[:, :, 1] * 0.7152
            + pixels[:, :, 2] * 0.0722
        )
        rr = gray * (1 - spill_val) + pixels[:, :, 0] * spill_val
        gg = gray * (1 - spill_val) + pixels[:, :, 1] * spill_val
        bb = gray * (1 - spill_val) + pixels[:, :, 2] * spill_val

        strength = np.minimum(1, spill_str * (1.2 - spill_val * 0.4))

        # Green screen spill: clamp G toward (R+B)/2
        if kg >= kr and kg >= kb:
            limit = (rr + bb) / 2
            gg = gg - strength * (gg - limit)

        # Blue screen spill: clamp B toward (R+G)/2
        if kb >= kr and kb >= kg:
            limit = (rr + gg) / 2
            bb = bb - strength * (bb - limit)

        pixels[:, :, 0] = np.clip(rr, 0, 255)
        pixels[:, :, 1] = np.clip(gg, 0, 255)
        pixels[:, :, 2] = np.clip(bb, 0, 255)

    pixels[:, :, 3] = np.round(alpha * 255)

    result = Image.fromarray(pixels.astype(np.uint8), "RGBA")

    # Alpha erosion
    for _ in range(min(5, max(0, erosion_passes))):
        result = _erode_alpha(result)

    return result


def _erode_alpha(img: Image.Image) -> Image.Image:
    """3x3 min filter on alpha channel to remove edge artifacts."""
    arr = np.array(img, dtype=np.uint8)
    alpha = arr[:, :, 3].copy()
    h, w = alpha.shape
    padded = np.pad(alpha, 1, mode="edge")
    for y in range(h):
        for x in range(w):
            patch = padded[y : y + 3, x : x + 3]
            arr[y, x, 3] = patch.min()
    return Image.fromarray(arr, "RGBA")
