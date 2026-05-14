"""
OpenCV grid (mesh) detection for pixel art conversion.

Ported from FrameRonin frontend lib/pixellise/mesh.ts.
Algorithm from: https://github.com/KennethJAllen/proper-pixel-art

Pipeline:
  1. Crop 2px border, nearest-neighbor upscale
  2. Canny edge detection + HoughLinesP
  3. Cluster lines, homogenize to pixel grid
  4. Fallback to uniform mesh if detection fails
"""

import numpy as np

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

# Type alias: [vertical_lines, horizontal_lines]
Mesh = tuple[list[int], list[int]]


def _median(arr: list[float]) -> float:
    s = sorted(arr)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _percentile(sorted_arr: np.ndarray, p: float) -> float:
    if len(sorted_arr) == 0:
        return 0
    idx = (p / 100.0) * (len(sorted_arr) - 1)
    lo, hi = int(np.floor(idx)), int(np.ceil(idx))
    if lo == hi:
        return float(sorted_arr[lo])
    return float(sorted_arr[lo] * (hi - idx) + sorted_arr[hi] * (idx - lo))


def _cluster_lines(lines: list[int], threshold: int = 4) -> list[int]:
    """Merge nearby Hough lines within threshold, return cluster medians."""
    if not lines:
        return []
    sorted_lines = sorted(lines)
    clusters = [[sorted_lines[0]]]
    for v in sorted_lines[1:]:
        last_cluster = clusters[-1]
        if abs(v - last_cluster[-1]) <= threshold:
            last_cluster.append(v)
        else:
            clusters.append([v])
    return [round(_median([float(c) for c in cl])) for cl in clusters]


def _detect_grid_lines(closed: np.ndarray, width: int, height: int) -> Mesh:
    """Run HoughLinesP on closed edge image, return clustered vertical/horizontal lines."""
    lines_x = [0, width - 1]
    lines_y = [0, height - 1]

    lines = cv2.HoughLinesP(closed, 1, np.pi / 180, 100,
                            minLineLength=50, maxLineGap=10)

    deg15 = (15 * np.pi) / 180
    deg75 = (75 * np.pi) / 180

    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                continue
            angle = abs(np.arctan2(float(dy), float(dx)))
            if angle > deg75:
                lines_x.append(round((x1 + x2) / 2))
            elif angle < deg15:
                lines_y.append(round((y1 + y2) / 2))

    return _cluster_lines(lines_x, 4), _cluster_lines(lines_y, 4)


def _get_pixel_width(mesh: Mesh, trim_outlier_frac: float = 0.2) -> float:
    """Estimate pixel width from gaps between grid lines."""
    gaps: list[float] = []
    for lines in mesh:
        for i in range(len(lines) - 1):
            gaps.append(float(lines[i + 1] - lines[i]))
    if not gaps:
        return 8
    gaps_sorted = sorted(gaps)
    low = _percentile(np.array(gaps_sorted), 100 * trim_outlier_frac)
    hi = _percentile(np.array(gaps_sorted), 100 * (1 - trim_outlier_frac))
    middle = [g for g in gaps_sorted if low <= g <= hi]
    use = middle if middle else gaps_sorted
    return _median(use)


def _homogenize_lines(lines: list[int], pixel_width: float) -> list[int]:
    """Snap lines to a regular pixel grid based on estimated pixel width."""
    n = len(lines)
    if n < 2:
        return list(lines)

    section_widths = [lines[i + 1] - lines[i] for i in range(n - 1)]
    pw = max(1.0, pixel_width)

    pieces: list[list[int]] = []
    for i in range(n - 1):
        line_start = lines[i]
        sw = section_widths[i]
        num_pixels = max(0, round(sw / pw))
        if num_pixels <= 0:
            pieces.append([])
            continue
        section_pw = sw / num_pixels
        section_lines = [line_start + int(np.floor(nn * section_pw)) for nn in range(num_pixels)]
        pieces.append(section_lines)

    flat = [v for sub in pieces for v in sub]
    flat.append(lines[-1])
    return sorted(set(flat))


def _is_trivial_mesh(mesh: Mesh) -> bool:
    xn, yn = len(mesh[0]), len(mesh[1])
    return (xn == 2 or xn == 3) and (yn == 2 or yn == 3)


def _crop_border(arr: np.ndarray, border: int = 2) -> np.ndarray:
    """Crop border pixels from RGBA image array."""
    h, w = arr.shape[:2]
    return arr[border:h - border, border:w - border].copy()


def _clamp_alpha_composite(arr: np.ndarray) -> np.ndarray:
    """Clamp alpha for edge detection (composite over white)."""
    h, w = arr.shape[:2]
    result = np.zeros((h, w, 4), dtype=np.uint8)
    alpha = arr[:, :, 3].astype(np.float32) / 255.0
    for c in range(3):
        result[:, :, c] = np.clip(arr[:, :, c].astype(np.float32) * alpha + 255 * (1 - alpha), 0, 255).astype(np.uint8)
    result[:, :, 3] = 255
    return result


def compute_mesh_on_image(rgba: np.ndarray, closure_kernel_size: int = 8) -> Mesh:
    """Detect pixel grid mesh from RGBA image array."""
    cropped = _crop_border(rgba, 2)
    ch, cw = cropped.shape[:2]

    if cw < 16 or ch < 16:
        return ([0, cw - 1], [0, ch - 1])

    composite = _clamp_alpha_composite(cropped)
    gray = cv2.cvtColor(composite, cv2.COLOR_RGBA2GRAY)
    edges = cv2.Canny(gray, 50, 200)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (closure_kernel_size, closure_kernel_size))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    mesh_init = _detect_grid_lines(closed, cw, ch)
    pixel_width = max(2.0, _get_pixel_width(mesh_init))
    lines_x = _homogenize_lines(mesh_init[0], pixel_width)
    lines_y = _homogenize_lines(mesh_init[1], pixel_width)

    return lines_x, lines_y


def _shift_cropped_to_full(mesh: Mesh, full_w: int, full_h: int) -> Mesh:
    """Shift mesh from cropped space (+2 border) back to full image coordinates."""
    vx = sorted(set([0] + [x + 2 for x in mesh[0]] + [full_w]))
    hy = sorted(set([0] + [y + 2 for y in mesh[1]] + [full_h]))
    return vx, hy


def _fallback_uniform_mesh(full_w: int, full_h: int, cell: int = 8) -> Mesh:
    """Create uniform grid when mesh detection fails."""
    c = max(4, int(cell))
    vx = [0]
    for x in range(c, full_w, c):
        vx.append(x)
    if vx[-1] < full_w:
        vx.append(full_w)
    hy = [0]
    for y in range(c, full_h, c):
        hy.append(y)
    if hy[-1] < full_h:
        hy.append(full_h)
    return vx, hy


def compute_mesh_with_scaling(
    rgba: np.ndarray,
    upscale: int = 1,
) -> tuple[Mesh, int, int, int]:
    """
    Detect pixel grid mesh with optional nearest-neighbor upscaling.

    Args:
        rgba: RGBA image as numpy array.
        upscale: Nearest-neighbor scale before mesh detection (1-7).

    Returns:
        (mesh, scale_used, scaled_width, scaled_height)
    """
    if not HAS_OPENCV:
        h, w = rgba.shape[:2]
        return _fallback_uniform_mesh(w, h), 1, w, h

    h, w = rgba.shape[:2]
    u = max(1, min(7, int(upscale)))
    sw, sh = round(w * u), round(h * u)

    # Nearest-neighbor upscale
    upscaled = np.repeat(np.repeat(rgba, u, axis=0), u, axis=1)
    mesh_crop = compute_mesh_on_image(upscaled)
    scale_used = u

    if _is_trivial_mesh(mesh_crop):
        mesh_crop = compute_mesh_on_image(rgba)
        scale_used = 1

    fw = sw if scale_used == u else w
    fh = sh if scale_used == u else h
    mesh = _shift_cropped_to_full(mesh_crop, fw, fh)

    if len(mesh[0]) < 3 or len(mesh[1]) < 3:
        mesh = _fallback_uniform_mesh(fw, fh, max(8, min(fw, fh) // 24))

    return mesh, scale_used, fw, fh
