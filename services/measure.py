# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
Ruler-based bolt measurement using OpenCV.

How it works:
  1. Find the metric ruler in the lower portion of the image (must be HORIZONTAL).
  2. Detect tick marks → compute pixels-per-mm scale factor.
  3. Find the bolt — the largest elongated object ABOVE the ruler that is NOT
     the ruler itself (enforced by width cap and gap constraints).
  4. Convert bolt pixel dimensions to mm.
  5. Snap to nearest standard bolt size (diameter × length).

Failure modes handled:
  - Vertical ruler → rejected (Hough only finds horizontal lines)
  - Ruler detected as bolt → rejected (bolt width capped at 80% of image width)
  - Short bolt at ruler edge → rejected (minimum gap above ruler enforced)
  - Wildly wrong diameter → sanity-checked and rejected
"""
import cv2
import numpy as np
from PIL import Image
from dataclasses import dataclass, field
from typing import Optional, Tuple, List


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class MeasureResult:
    length_mm: float          # measured bolt length
    diameter_mm: float        # measured bolt shank width
    pixels_per_mm: float      # computed scale factor
    confidence: str           # 'high' | 'medium' | 'low'
    nearest_label: str        # e.g. "8mm_70mm"
    debug: dict = field(default_factory=dict)


# ── Main entry point ───────────────────────────────────────────────────────────

def measure_bolt(pil_image: Image.Image) -> Optional[MeasureResult]:
    """
    Returns MeasureResult or None if ruler / bolt cannot be detected.
    """
    img_rgb = np.array(pil_image.convert("RGB"))
    bgr     = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h, w    = bgr.shape[:2]

    # ── Step 1: find ruler and scale ──────────────────────────────────────────
    scale = _detect_ruler_scale(bgr)
    if scale is None:
        return None
    pixels_per_mm, ruler_y = scale

    # ── Step 2: find bolt bounding box (above ruler, not the ruler itself) ────
    bolt_rect = _detect_bolt(bgr, ruler_y)
    if bolt_rect is None:
        return None
    bx, by, bw, bh = bolt_rect

    # ── Step 3: convert pixels → mm ──────────────────────────────────────────
    length_mm   = bw / pixels_per_mm

    # Measure shank diameter from the MIDDLE 50% of the bolt (skip hex head & tip).
    # The hex head is at the left end and is wider than the shank. Measuring the
    # full bounding box height gives head width (~13mm for M8) not shank (8mm).
    diameter_mm = _measure_shank_diameter(bgr, bolt_rect, ruler_y) / pixels_per_mm

    # ── Step 4: sanity checks — reject obviously wrong measurements ───────────
    if length_mm < 8 or length_mm > 400:
        return None
    if diameter_mm < 2 or diameter_mm > 40:
        return None
    if length_mm / max(diameter_mm, 1) < 1.5:
        return None   # not elongated enough to be a bolt

    # ── Step 5: snap to nearest standard size ────────────────────────────────
    nearest = _nearest_label(length_mm, diameter_mm)

    # ── Step 6: compute confidence ────────────────────────────────────────────
    parts = nearest.split('_')
    std_d = int(parts[0].replace('mm', ''))
    std_l = int(parts[1].replace('mm', ''))
    len_err = abs(length_mm - std_l)
    dia_err = abs(diameter_mm - std_d)

    if   len_err <= 5  and dia_err <= 2:  confidence = 'high'
    elif len_err <= 12 and dia_err <= 4:  confidence = 'medium'
    else:                                  confidence = 'low'

    return MeasureResult(
        length_mm     = round(length_mm,   1),
        diameter_mm   = round(diameter_mm, 1),
        pixels_per_mm = round(pixels_per_mm, 2),
        confidence    = confidence,
        nearest_label = nearest,
        debug = {
            'bolt_rect': bolt_rect,
            'ruler_y':   ruler_y,
            'std_label': f'M{std_d}×{std_l}mm',
        },
    )


# ── Ruler detection ────────────────────────────────────────────────────────────

def _detect_ruler_scale(bgr: np.ndarray) -> Optional[Tuple[float, int]]:
    """
    Returns (pixels_per_mm, ruler_y) or None.
    Searches the bottom 50% of the image for a long horizontal line,
    then measures tick mark spacing to get the px/mm scale.
    """
    h, w = bgr.shape[:2]

    # Search bottom 50% of image for the ruler
    search_top = int(h * 0.50)
    roi  = bgr[search_top:, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 40, 120)

    # Hough: only finds HORIZONTAL lines — vertical ruler will naturally fail
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold     = max(50, int(w * 0.18)),
        minLineLength = max(80, int(w * 0.22)),
        maxLineGap    = 50,
    )
    if lines is None:
        return None

    # Pick the longest roughly-horizontal line as the ruler baseline
    ruler_line = None
    max_len    = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 10:                      # within 10° of horizontal
            ln = abs(x2 - x1)
            if ln > max_len:
                max_len    = ln
                ruler_line = (x1, y1, x2, y2)

    if ruler_line is None:
        return None

    rx1, ry1, rx2, ry2 = ruler_line
    ruler_y = search_top + (ry1 + ry2) // 2

    # Extract a strip around the ruler to find tick mark spacing
    strip_h = 40
    sy_top = max(0, ruler_y - strip_h)
    sy_bot = min(h, ruler_y + 10)
    strip  = cv2.cvtColor(bgr[sy_top:sy_bot, :], cv2.COLOR_BGR2GRAY)

    # Binarise: tick marks are dark on a light (white/yellow) ruler
    _, binary = cv2.threshold(strip, 0, 255,
                              cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # Vertical projection: where are the dark tick marks?
    projection = binary.sum(axis=0).astype(float)
    if projection.max() == 0:
        return None
    projection /= projection.max()

    peaks = _find_peaks(projection, min_height=0.18, min_distance=3)
    if len(peaks) < 6:
        return None

    spacings  = np.diff(peaks).astype(float)
    median_sp = np.median(spacings)
    # Keep only consistent spacings (within 50% of median)
    spacings  = spacings[np.abs(spacings - median_sp) < median_sp * 0.5]
    if len(spacings) < 3:
        return None

    px_per_mm = float(np.mean(spacings))

    # Sanity: 1 mm should be 4–35 px at normal photo distances
    if not (4.0 < px_per_mm < 35.0):
        return None

    return px_per_mm, ruler_y


# ── Bolt detection ─────────────────────────────────────────────────────────────

def _detect_bolt(bgr: np.ndarray, ruler_y: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Returns (x, y, width, height) bounding rect of the bolt.

    Key constraints that prevent detecting the ruler as the bolt:
      - Search region ends GAP pixels ABOVE the ruler (not at ruler_y)
      - Detected contour width must be < 80% of image width
      - Contour must be elongated (width / height >= 2.5)
    """
    h, w = bgr.shape[:2]

    # Leave a gap above the ruler so we never accidentally grab the ruler body
    GAP = 25   # pixels
    top_margin   = int(h * 0.04)
    search_bottom = ruler_y - GAP

    if search_bottom <= top_margin + 40:
        return None   # too little space above ruler

    roi   = bgr[top_margin:search_bottom, :]
    roi_h = roi.shape[0]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold handles both dark and light backgrounds
    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=51,
        C=-8,
    )
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
    closed   = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_h)

    # Canny-based fallback
    edges   = cv2.Canny(blur, 30, 100)
    kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    closed2 = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel2)

    best       = None
    best_score = 0

    for mask in (closed, closed2):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < roi_h * w * 0.003:   # too small
                continue

            x, y, cw, ch = cv2.boundingRect(cnt)

            # ── Reject if it spans most of the image — that's the ruler, not the bolt
            if cw > w * 0.80:
                continue

            if ch == 0:
                continue

            ratio = cw / ch
            if ratio < 2.5:               # must be clearly elongated
                continue

            # Prefer large + elongated contours
            score = area * ratio
            if score > best_score:
                best_score = score
                best = (x, y + top_margin, cw, ch)

    return best


# ── Shank diameter measurement ────────────────────────────────────────────────

def _measure_shank_diameter(bgr: np.ndarray,
                             bolt_rect: Tuple[int, int, int, int],
                             ruler_y: int) -> float:
    """
    Measure the bolt SHANK width by scanning only the middle 50% of the bolt's
    horizontal span (skipping the hex head on the left and the tip on the right).

    For each column in that zone, finds the topmost and bottommost bolt pixels
    and computes the vertical span. Returns the median of those spans in pixels.
    Falls back to bounding box height if scanning fails.
    """
    bx, by, bw, bh = bolt_rect
    h, w = bgr.shape[:2]

    # Middle 50% of bolt length — avoids hex head (left ~25%) and tip (right ~15%)
    x_start = bx + int(bw * 0.25)
    x_end   = bx + int(bw * 0.75)
    if x_end <= x_start:
        return float(bh)

    # Extract the ROI strip for this zone (above ruler only)
    y_top = max(0, by - 5)
    y_bot = min(ruler_y, by + bh + 5)
    strip = bgr[y_top:y_bot, x_start:x_end]

    if strip.size == 0:
        return float(bh)

    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # Threshold: bolt is bright (metallic) or dark depending on background
    _, thresh_bright = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    _, thresh_dark   = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    spans = []
    strip_h = strip.shape[0]

    for thresh in (thresh_bright, thresh_dark):
        col_spans = []
        for col in range(thresh.shape[1]):
            col_data = thresh[:, col]
            nonzero  = np.where(col_data > 0)[0]
            if len(nonzero) < 3:
                continue
            span = int(nonzero[-1]) - int(nonzero[0])
            # Ignore spans that are too thin (noise) or too tall (grabbed background)
            if 3 < span < strip_h * 0.9:
                col_spans.append(span)
        if col_spans:
            spans.extend(col_spans)

    if not spans:
        return float(bh)

    # Use the median to reject outliers from reflections / shadows
    return float(np.median(spans))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_peaks(arr: np.ndarray,
                min_height: float = 0.0,
                min_distance: int = 3) -> List[int]:
    """Simple peak finder — no scipy dependency."""
    peaks: List[int] = []
    for i in range(1, len(arr) - 1):
        if arr[i] >= min_height and arr[i] > arr[i-1] and arr[i] > arr[i+1]:
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    return peaks


# ── Standard bolt size catalogue ───────────────────────────────────────────────

_STANDARD_SIZES: List[Tuple[int, int]] = [
    (4,10),(4,16),(4,20),(4,25),(4,30),(4,40),(4,50),
    (5,10),(5,16),(5,20),(5,25),(5,30),(5,40),(5,50),
    (6,12),(6,16),(6,20),(6,25),(6,30),(6,40),(6,50),(6,60),(6,70),(6,80),(6,100),(6,120),
    (8,16),(8,20),(8,25),(8,30),(8,40),(8,50),(8,60),(8,70),(8,80),(8,100),(8,120),(8,150),
    (10,16),(10,20),(10,25),(10,30),(10,40),(10,45),(10,50),(10,60),(10,70),(10,80),
    (10,90),(10,100),(10,120),(10,140),(10,150),(10,160),
    (12,20),(12,25),(12,30),(12,40),(12,45),(12,50),(12,60),(12,70),(12,80),(12,90),
    (12,100),(12,120),(12,140),(12,150),(12,160),(12,180),
    (14,25),(14,30),(14,35),(14,40),(14,45),(14,50),(14,60),(14,70),(14,80),(14,90),
    (14,100),(14,120),(14,140),(14,150),(14,160),(14,180),(14,200),(14,220),
    (16,25),(16,30),(16,35),(16,40),(16,45),(16,50),(16,55),(16,60),(16,70),(16,80),
    (16,90),(16,100),(16,120),(16,130),(16,140),(16,150),(16,160),(16,180),(16,200),
    (16,220),(16,240),(16,260),
    (18,40),(18,50),(18,60),(18,70),(18,80),(18,90),(18,100),(18,120),(18,140),(18,160),
    (18,180),(18,200),
    (20,40),(20,50),(20,60),(20,70),(20,80),(20,90),(20,100),(20,110),(20,120),(20,130),
    (20,140),(20,150),(20,160),(20,180),(20,200),(20,220),(20,240),
    (22,50),(22,60),(22,70),(22,80),(22,90),(22,100),(22,120),(22,140),(22,160),(22,180),
    (24,50),(24,60),(24,70),(24,80),(24,90),(24,100),(24,120),(24,140),(24,160),(24,180),
    (24,200),(24,220),(24,260),
    (27,60),(27,70),(27,80),(27,100),(27,120),(27,130),(27,140),(27,160),(27,220),(27,280),
    (30,60),(30,70),(30,80),(30,90),(30,100),(30,120),(30,130),(30,140),(30,150),(30,160),
    (30,180),(30,200),
    (33,100),(33,120),(33,140),(33,180),(33,200),(33,220),(33,250),
    (36,120),(36,160),
    (39,160),
]


def _nearest_label(length_mm: float, diameter_mm: float) -> str:
    """
    Snap measured dimensions to the nearest standard bolt size.

    Weighting rationale:
      - Length is measured more reliably (longer span → more pixels → less % error)
      - Diameter is noisier (only ~10–30px for small bolts) so weighted less
      - Length weight 1×, diameter weight 1.5× (reduced from 3× to avoid over-penalising
        diameter measurement noise)
    """
    best_label = '8mm_30mm'
    best_dist  = float('inf')
    for d, l in _STANDARD_SIZES:
        dist = (length_mm - l) ** 2 + 1.5 * (diameter_mm - d) ** 2
        if dist < best_dist:
            best_dist  = dist
            best_label = f'{d}mm_{l}mm'
    return best_label
