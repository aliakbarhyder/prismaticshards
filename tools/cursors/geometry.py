#!/usr/bin/env python3
"""Original vector geometry for the Prismatic-Shards cursor theme.

Everything is authored in a unit box (see ``raster.py``): (0, 0) is the top
left of the square cursor image, (1, 1) the bottom right.  Hot spots are stored
as fractions of that box, because that is exactly what hyprcursor wants
(``round(size * hotspot_x)`` gives the pixel hot spot) and what the xcursor
writer derives its per-size pixel hot spots from.

Design language -- "fractured light, unified system"
----------------------------------------------------
* near-white glass body (``#F5F7FA``) with a 1.5 px @32 dark outline,
* prismatic blue (``#4DA3FF``) for the active edge / progress arc / glyphs,
* a thin violet (``#8B7CFF``) refraction highlight that fades out along one
  edge of the glass,
* a soft ``#08090B`` drop shadow at 18 % alpha, offset (0, 0.04).

All artwork here is original: silhouettes are composed from primitives and
hand-placed control points authored for this theme (no third-party icon data).
The outlines are drawn *before* the fills by ``raster.render`` so that
overlapping primitives merge into one silhouette with a single outer outline.
"""

from __future__ import annotations

import math

from raster import (Part, Stroke, annulus, arc, circle, fillet, flatten,
                    rounded_rect, stadium, polygon, Path, OUTLINE_WIDTH)

# --------------------------------------------------------------------------
# Design tokens
# --------------------------------------------------------------------------

SQRT1_2 = 0.7071067811865476

OUTLINE_W = OUTLINE_WIDTH        # 1.5 px @32, scales with the size
REFRACTION_WIDTH = 0.75 / 32.0              # 0.75 px @32, scales with the size

#: Refraction fade: five pieces along the edge, dimming towards the far end.
FADE_ALPHAS = (0.42, 0.32, 0.22, 0.13, 0.05)


def lerp(p0, p1, t: float):
    return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)


def add(p, v):
    return (p[0] + v[0], p[1] + v[1])


def sub(p, v):
    return (p[0] - v[0], p[1] - v[1])


def mul(v, k: float):
    return (v[0] * k, v[1] * k)


def norm(v):
    length = math.hypot(v[0], v[1])
    if length <= 1e-12:
        raise ValueError("zero-length vector")
    return (v[0] / length, v[1] / length)


def perp(p0, p1):
    """Unit normal of the direction ``p0 -> p1`` (rotated +90 deg on screen)."""
    d = norm(sub(p1, p0))
    return (d[1], -d[0])


def line_intersection(p0, d0, p1, d1):
    """Intersection of the lines ``p0 + t*d0`` and ``p1 + u*d1``."""
    denom = d0[0] * d1[1] - d0[1] * d1[0]
    if abs(denom) <= 1e-12:
        raise ValueError("parallel lines")
    t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / denom
    return add(p0, mul(d0, t))


def edge_glint(p0, p1, amount: float, width: float, role: str = "accent",
               alpha: float = 0.92, t0: float = 0.0, t1: float = 1.0,
               min_size: int = 0, cap: str = "round") -> Stroke:
    """A short parallel stroke inside the edge ``p0 -> p1``.

    ``amount`` is the inward offset in unit space; ``t0``/``t1`` trim the
    glint so it never reaches the silhouette outline.
    """
    normal = perp(p0, p1)
    a = add(lerp(p0, p1, t0), mul(normal, amount))
    b = add(lerp(p0, p1, t1), mul(normal, amount))
    return Stroke(Path.from_points([a, b], close=False), width, role, alpha,
                  min_size, cap=cap)


def fading(path: Path, width: float = REFRACTION_WIDTH, role: str = "refract",
           alphas=FADE_ALPHAS, min_size: int = 32) -> list[Stroke]:
    """Split a centre line into pieces with decreasing alpha (refraction)."""
    points, _ = flatten(path)
    strokes = []
    count = len(alphas)
    for i in range(count):
        a = i * (len(points) - 1) // count
        b = (i + 1) * (len(points) - 1) // count
        piece = points[a:b + 1]
        if len(piece) < 2:
            continue
        strokes.append(Stroke(Path.from_points(piece, close=False), width,
                              role, alphas[i], min_size, cap="round"))
    return strokes


# --------------------------------------------------------------------------
# Shape container
# --------------------------------------------------------------------------

class Shape:
    """One cursor shape: name, aliases, hot spot and its paint operations."""

    __slots__ = ("name", "aliases", "xcursor", "hotspot", "parts", "strokes")

    def __init__(self, name: str, aliases, xcursor: str, hotspot,
                 parts, strokes=()):
        self.name = name
        self.aliases = tuple(aliases)
        self.xcursor = xcursor
        self.hotspot = (float(hotspot[0]), float(hotspot[1]))
        self.parts = list(parts)
        self.strokes = list(strokes)


# --------------------------------------------------------------------------
# Shared sub-shapes
# --------------------------------------------------------------------------

#: Arrow outline control points (unit space, tip at the top-left corner).
ARROW_TIP = (0.0625, 0.0625)
ARROW_LEFT = (0.0625, 0.6250)        # bottom of the straight leading edge
ARROW_RIGHT = (0.4375, 0.4375)       # end of the 45 degree leading edge
ARROW_TAIL_START = 0.30              # where the tail leaves the trailing edge
ARROW_TAIL_LENGTH = 0.235
ARROW_TAIL_WIDTH = 0.135


def arrow_path() -> Path:
    """The slim pointer: 45 degree leading edge plus a 45 degree tail.

    The tail's outer corner is the exact intersection of the tail's upper side
    with the blade's trailing edge, which keeps the silhouette a simple polygon
    (no spurs) while still showing the classic notch between blade and tail.
    """
    tip = ARROW_TIP
    left = ARROW_LEFT
    right = ARROW_RIGHT
    along = sub(right, left)
    tail_start = lerp(left, right, ARROW_TAIL_START)
    direction = (SQRT1_2, SQRT1_2)               # 45 degrees, down-right
    normal = (SQRT1_2, -SQRT1_2)                 # up-right
    start_corner = add(tail_start, mul(normal, ARROW_TAIL_WIDTH))
    # Outer corner: where the tail's upper side meets the trailing edge.
    outer = line_intersection(start_corner, direction, left, along)
    tail_end = add(tail_start, mul(direction, ARROW_TAIL_LENGTH))
    tail_outer_end = add(tail_end, mul(normal, ARROW_TAIL_WIDTH))
    return fillet([tip, left, tail_start, tail_end, tail_outer_end, outer,
                   right], radius=0.026, radius_first=0.010)


def arrow_glint() -> Stroke:
    """Prismatic-blue glint along the arrow's leading (active) edge."""
    return edge_glint(ARROW_RIGHT, ARROW_TIP, 0.048, 0.030, "accent", 0.92,
                      t0=0.16, t1=0.62)


def arrow_refraction(min_size: int = 24):
    """Violet refraction highlight along the arrow's trailing edge."""
    path = Path.from_points([(0.0925, 0.135), (0.0925, 0.560)], close=False)
    return fading(path, REFRACTION_WIDTH, "refract", FADE_ALPHAS, min_size)




# --------------------------------------------------------------------------
# Individual shapes
# --------------------------------------------------------------------------

def shape_default() -> Shape:
    """Pointer arrow: slim blade, 45 degree tail, blue active edge."""
    strokes = [arrow_glint(), *arrow_refraction()]
    return Shape("default",
                 ("left_ptr", "default", "arrow", "top_left_arrow"),
                 "left_ptr.xcur", ARROW_TIP, [Part(arrow_path())], strokes)


def shape_pointer() -> Shape:
    """Pointing hand: extended index finger, thumb, three folded fingers."""
    parts = [
        Part(stadium(0.375, 0.520, 0.375, 0.145, 0.200)),         # index
        Part(rounded_rect(0.270, 0.340, 0.845, 0.875, 0.130)),    # palm
        Part(stadium(0.400, 0.560, 0.160, 0.500, 0.175)),         # thumb
        Part(stadium(0.600, 0.435, 0.845, 0.435, 0.160)),         # folded 1
        Part(stadium(0.615, 0.575, 0.845, 0.575, 0.155)),         # folded 2
        Part(stadium(0.620, 0.715, 0.845, 0.715, 0.155)),         # folded 3
    ]
    fingertip_arc = Path.from_points(
        [(0.375 + 0.065 * math.cos(math.radians(a)),
          0.145 + 0.065 * math.sin(math.radians(a)))
         for a in range(196, 345, 6)], close=False)
    strokes = [
        # Blue crescent inside the fingertip: the "active point" of the hand.
        Stroke(fingertip_arc, 0.030, "accent", 0.92, 0),
        *fading(Path.from_points([(0.3075, 0.180), (0.3075, 0.460)],
                                 close=False), REFRACTION_WIDTH, "refract",
                FADE_ALPHAS, 32),
    ]
    return Shape("pointer", ("hand2", "hand", "pointer", "pointing_hand"),
                 "hand2.xcur", (0.375, 0.045), parts, strokes)


def shape_text() -> Shape:
    """I-beam: 3 px @32 stem with serifs and blue serif accents."""
    stem = 0.046875      # -> 3 px at 32 px
    serif = 0.125        # -> 8 px at 32 px
    top, thickness, bottom = 0.09375, 0.09375, 0.90625
    centre = 0.5
    body = fillet([
        (centre - serif, top), (centre + serif, top),
        (centre + serif, top + thickness), (centre + stem, top + thickness),
        (centre + stem, bottom - thickness),
        (centre + serif, bottom - thickness),
        (centre + serif, bottom), (centre - serif, bottom),
        (centre - serif, bottom - thickness),
        (centre - stem, bottom - thickness),
        (centre - stem, top + thickness), (centre - serif, top + thickness),
    ], radius=0.010)
    parts = [
        Part(body),
        # Blue accent bars: the "active edge" of the insertion point.
        Part(polygon((0.400, top + thickness), (0.600, top + thickness),
                     (0.600, top + thickness + 0.039),
                     (0.400, top + thickness + 0.039)),
             role="accent", outline=False),
        Part(polygon((0.400, bottom - thickness - 0.039),
                     (0.600, bottom - thickness - 0.039),
                     (0.600, bottom - thickness), (0.400, bottom - thickness)),
             role="accent", outline=False),
    ]
    strokes = fading(Path.from_points([(0.525, 0.240), (0.525, 0.760)],
                                      close=False), 0.020, "refract",
                     FADE_ALPHAS, 48)
    return Shape("text", ("xterm", "ibeam", "text"), "xterm.xcur",
                 (0.5, 0.5), parts, strokes)


def shape_grab() -> Shape:
    """Open hand: palm + four fingers + thumb, blue fingertip arc."""
    parts = [
        Part(rounded_rect(0.26, 0.38, 0.80, 0.86, 0.12)),
        Part(stadium(0.32, 0.42, 0.32, 0.16, 0.16)),
        Part(stadium(0.46, 0.42, 0.46, 0.12, 0.16)),
        Part(stadium(0.60, 0.42, 0.60, 0.15, 0.16)),
        Part(stadium(0.73, 0.46, 0.73, 0.24, 0.15)),
        Part(stadium(0.34, 0.58, 0.14, 0.50, 0.16)),
    ]
    tip_arc = Path.from_points(
        [(0.46 + 0.062 * math.cos(math.radians(a)),
          0.12 + 0.062 * math.sin(math.radians(a)))
         for a in range(195, 345, 6)], close=False)
    strokes = [Stroke(tip_arc, 0.028, "accent", 0.90, 0)]
    return Shape("grab", ("grab", "open_hand", "fleur"), "grab.xcur",
                 (0.46, 0.10), parts, strokes)


def shape_grabbing() -> Shape:
    """Closed hand: rounded fist + thumb bar, blue knuckle glint."""
    parts = [
        Part(rounded_rect(0.24, 0.40, 0.82, 0.88, 0.16)),
        Part(stadium(0.30, 0.52, 0.78, 0.52, 0.17)),
        Part(stadium(0.30, 0.66, 0.78, 0.66, 0.17)),
        Part(stadium(0.36, 0.56, 0.16, 0.50, 0.15)),
    ]
    strokes = [edge_glint((0.30, 0.435), (0.78, 0.435), 0.030, 0.026,
                          "accent", 0.88, t0=0.15, t1=0.85)]
    return Shape("grabbing", ("grabbing", "closed_hand", "dnd-none"),
                 "grabbing.xcur", (0.5, 0.55), parts, strokes)


def shape_resize() -> Shape:
    """Diagonal double arrow: shaft + two heads, blue shaft glint."""
    shaft = polygon((0.24, 0.44), (0.70, 0.44), (0.70, 0.56), (0.24, 0.56))
    head_a = polygon((0.10, 0.50), (0.28, 0.36), (0.28, 0.64))
    head_b = polygon((0.90, 0.50), (0.72, 0.36), (0.72, 0.64))
    parts = [Part(shaft), Part(head_a), Part(head_b)]
    strokes = [edge_glint((0.26, 0.47), (0.68, 0.47), 0.012, 0.020,
                          "accent", 0.90, t0=0.05, t1=0.95)]
    return Shape("resize", ("sizing", "bottom_right_corner", "fleur"),
                 "sizing.xcur", (0.5, 0.5), parts, strokes)


def _ring_parts(cx: float, cy: float, r_out: float, width: float):
    r_in = max(0.01, r_out - width)
    rings = annulus(cx, cy, r_out, r_in)
    return [Part(r, outline=False) for r in rings]


def shape_wait() -> Shape:
    """Hourglass ring + prismatic progress arc."""
    parts = _ring_parts(0.5, 0.5, 0.30, 0.085)
    prog = arc(0.5, 0.5, 0.30, -90.0, 90.0)
    strokes = [Stroke(prog, 0.085, "accent", 0.95, 0)]
    return Shape("wait", ("wait", "watch", "progress"), "wait.xcur",
                 (0.5, 0.5), parts, strokes)


def shape_progress() -> Shape:
    """Small arrow + waiting ring (arrow with progress halo)."""
    parts = [Part(arrow_path()),
             _ring_parts(0.68, 0.68, 0.16, 0.06)[0]]
    strokes = [arrow_glint(),
               Stroke(arc(0.68, 0.68, 0.16, -90.0, 150.0), 0.06,
                      "accent", 0.95, 0)]
    return Shape("progress", ("left_ptr_watch", "progress", "wait"),
                 "left_ptr_watch.xcur", ARROW_TIP, parts, strokes)


def shape_crosshair() -> Shape:
    """Crosshair: thin bars + centre ring, blue centre dot."""
    bar = 0.035
    parts = [
        Part(polygon((0.5 - bar, 0.08), (0.5 + bar, 0.08),
                     (0.5 + bar, 0.92), (0.5 - bar, 0.92)), outline=False),
        Part(polygon((0.08, 0.5 - bar), (0.92, 0.5 - bar),
                     (0.92, 0.5 + bar), (0.08, 0.5 + bar)), outline=False),
        Part(circle(0.5, 0.5, 0.045), role="accent", outline=False),
    ]
    return Shape("crosshair", ("crosshair", "cross", "tcross"),
                 "cross.xcur", (0.5, 0.5), parts, ())


def shape_not_allowed() -> Shape:
    """Prohibited: ring + diagonal bar, red danger bar."""
    rings = annulus(0.5, 0.5, 0.32, 0.235)
    bar = polygon((0.24, 0.62), (0.38, 0.70), (0.76, 0.30), (0.62, 0.22))
    parts = [Part(r, outline=True) for r in rings]
    parts.append(Part(bar, role="danger", outline=False))
    return Shape("not-allowed",
                 ("not-allowed", "crossed_circle", "no-drop", "dnd-no-drop"),
                 "not-allowed.xcur", (0.5, 0.5), parts, ())


def shape_help() -> Shape:
    """Help bubble: rounded body + question glyph (accent)."""
    parts = [
        Part(rounded_rect(0.22, 0.14, 0.78, 0.72, 0.16)),
        Part(polygon((0.34, 0.72), (0.30, 0.88), (0.50, 0.72)), outline=False),
        Part(circle(0.5, 0.46, 0.055), role="accent", outline=False),
        Part(stadium(0.5, 0.42, 0.5, 0.28, 0.09), role="accent",
             outline=False),
    ]
    return Shape("help", ("help", "question_arrow", "whats_this"),
                 "help.xcur", (0.15, 0.05), parts, ())


def shape_zoom() -> Shape:
    """Magnifier: ring + handle, blue handle glint."""
    rings = annulus(0.42, 0.42, 0.26, 0.175)
    handle = stadium(0.58, 0.58, 0.82, 0.82, 0.11)
    parts = [Part(r) for r in rings] + [Part(handle)]
    strokes = [edge_glint((0.60, 0.60), (0.80, 0.80), 0.020, 0.026,
                          "accent", 0.90, t0=0.1, t1=0.9)]
    return Shape("zoom", ("zoom-in", "zoom-out", "magnifier"),
                 "zoom-in.xcur", (0.42, 0.42), parts, strokes)


def all_shapes() -> list:
    """Every cursor shape in shipping order."""
    return [
        shape_default(), shape_pointer(), shape_text(),
        shape_grab(), shape_grabbing(), shape_resize(),
        shape_wait(), shape_progress(), shape_crosshair(),
        shape_not_allowed(), shape_help(), shape_zoom(),
    ]


# Compatibility shims for older tooling -------------------------------------
def vector_circle(*args, **kwargs):
    return circle(*args, **kwargs)


def vector_ring(*args, **kwargs):
    return annulus(*args, **kwargs)


def geometry(*args, **kwargs):  # noqa: D103 - legacy name
    return all_shapes()
