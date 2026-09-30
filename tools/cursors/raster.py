#!/usr/bin/env python3
"""Prismatic-Shards cursor rasterizer -- pure Python 3, standard library only.

Unit space
----------
Every cursor shape is authored in a square "unit box": (0, 0) is the top-left
corner of the cursor image, (1, 1) the bottom-right corner (y grows downward,
like every bitmap cursor format we touch).  The rasterizer scales that box to
whatever pixel size is requested, so one description produces 24/32/48/64 px
images without any bitmap resampling.

Pipeline
--------
1. ``Path`` holds move/line/quadratic/cubic/close segments in unit space.
2. ``flatten()`` converts them to polylines with a bounded chord error.
3. ``rasterize()`` computes per-pixel coverage with a scanline polygon fill on
   an ``SS x SS`` supersample grid (4x4 = 16 samples per pixel).  Nonzero and
   even-odd fill rules are both implemented.
4. ``stroke_outline()`` strokes a centre line by filling the union of one quad
   per segment plus one disc per joint ("stroke as filled outline").
5. ``render()`` composites the layers into a float RGBA canvas (straight
   alpha, source-over) and returns 8-bit row-major RGBA bytes.

Layer order (important)
-----------------------
Outlines are painted *first*, fills *afterwards*.  A part therefore keeps a
true silhouette outline: the half of an outline stroke that any fill covers
simply disappears, which is exactly how a union of overlapping primitives
should be outlined.  Accents/refraction are painted last, on top of the body.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------------

SS = 4                      # supersampling factor: 4x4 samples per pixel
FLATTEN_TOL = 0.0006        # max chord error in unit space (~0.04 px at 64 px)
_MAX_SUBDIV = 12            # recursion guard for bezier flattening
KAPPA = 0.5522847498307936  # control-point ratio for a 90 degree circular arc

#: Paint order of the roles.  Outlines first, then fills, then the highlights.
ROLE_ORDER = ("outline", "body", "danger", "accent", "refract")


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

#: The installed (high contrast / dark) cursor palette.
PALETTE_DARK = {
    "body": "#F5F7FA",      # near-white glass
    "outline": "#12151A",   # 1.5 px at 32 px, scaled with size
    "accent": "#4DA3FF",    # prismatic blue: active edge / arcs / glyphs
    "danger": "#FF6472",    # "stop" red, only used by not-allowed
    "refract": "#8B7CFF",   # violet refraction highlight (fading)
    "shadow": "#08090B",    # soft drop shadow at 18 % alpha
}

#: Preview-only light variant (see cursor/README.md -- not an installed theme).
PALETTE_LIGHT = {
    "body": "#16181C",
    "outline": "#FFFFFF",
    "accent": "#1677FF",
    "danger": "#D94350",
    "refract": "#705FE8",
    "shadow": "#08090B",
}

PALETTES = {
    "prismatic-shards": PALETTE_DARK,
    "prismatic-shards-light": PALETTE_LIGHT,
}

#: Drop shadow: offset (0, 0.04) unit, ~18 % alpha, radius scaled with size.
SHADOW_OFFSET_UNITS = (0.0, 0.04)
SHADOW_ALPHA = 0.18
SHADOW_RADIUS_RATIO = 0.025     # of the pixel size, at least 1 px
SHADOW_MIN_SIZE = 24            # only ever skipped below the sizes we ship


def parse_hex_rgb(value: str) -> tuple[float, float, float]:
    """``"#4DA3FF"`` -> ``(0.302, 0.639, 1.0)`` floats."""
    text = value.lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        raise ValueError(f"not a 6-digit hex colour: {value!r}")
    return tuple(int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]



# --------------------------------------------------------------------------
# Path model
# --------------------------------------------------------------------------

class Path:
    """A subpath made of line / quadratic / cubic segments in unit space.

    Segment tuples (all coordinates are floats in the unit box):

    ``("M", x, y)``             move to (starts the subpath)
    ``("L", x, y)``             line to
    ``("Q", cx, cy, x, y)``     quadratic bezier to (x, y)
    ``("C", c1x, c1y, c2x, c2y, x, y)``   cubic bezier to (x, y)
    ``("Z",)``                  close the subpath
    """

    __slots__ = ("segments",)

    def __init__(self, segments=None):
        self.segments = list(segments or ())

    # -- construction ------------------------------------------------------

    def move_to(self, x, y) -> "Path":
        self.segments.append(("M", float(x), float(y)))
        return self

    def line_to(self, x, y) -> "Path":
        self.segments.append(("L", float(x), float(y)))
        return self

    def quad_to(self, cx, cy, x, y) -> "Path":
        self.segments.append(("Q", float(cx), float(cy), float(x), float(y)))
        return self

    def cubic_to(self, c1x, c1y, c2x, c2y, x, y) -> "Path":
        self.segments.append(("C", float(c1x), float(c1y),
                              float(c2x), float(c2y), float(x), float(y)))
        return self

    def close(self) -> "Path":
        if self.segments and self.segments[-1][0] != "Z":
            self.segments.append(("Z",))
        return self

    # -- queries -----------------------------------------------------------

    @property
    def closed(self) -> bool:
        return bool(self.segments) and self.segments[-1][0] == "Z"

    @property
    def empty(self) -> bool:
        return not self.segments

    def copy(self) -> "Path":
        return Path(self.segments)

    def start_point(self) -> tuple[float, float]:
        for seg in self.segments:
            if seg[0] == "M":
                return (seg[1], seg[2])
        raise ValueError("path has no move_to")

    # -- helpers -----------------------------------------------------------

    @classmethod
    def from_points(cls, points, close: bool = True) -> "Path":
        """Build a polyline path from an iterable of ``(x, y)`` points."""
        pts = [(float(x), float(y)) for x, y in points]
        path = cls()
        if not pts:
            return path
        path.move_to(*pts[0])
        for pt in pts[1:]:
            path.line_to(*pt)
        if close:
            path.close()
        return path

    def transform(self, scale: float = 1.0, rotate: float = 0.0,
                  translate: tuple[float, float] = (0.0, 0.0),
                  pivot: tuple[float, float] = (0.0, 0.0)) -> "Path":
        """Affine copy: scale, then rotate (degrees, screen space), then move.

        Applied about ``pivot`` so a shape can be scaled or rotated in place::

            p' = R(rotate) * (p - pivot) * scale + pivot + translate
        """
        rad = math.radians(rotate)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        px, py = pivot
        tx, ty = translate

        def map_pt(x: float, y: float) -> tuple[float, float]:
            dx = (x - px) * scale
            dy = (y - py) * scale
            return (px + dx * cos_a - dy * sin_a + tx,
                    py + dx * sin_a + dy * cos_a + ty)

        out = Path()
        for seg in self.segments:
            if seg[0] == "Z":
                out.segments.append(("Z",))
                continue
            mapped = [seg[0]]
            for i in range(1, len(seg), 2):
                mx, my = map_pt(seg[i], seg[i + 1])
                mapped.extend((mx, my))
            out.segments.append(tuple(mapped))
        return out


# --------------------------------------------------------------------------
# Ring / primitive helpers
# --------------------------------------------------------------------------

def signed_area(points) -> float:
    """Shoelace signed area (positive == counter-clockwise in a y-down box)."""
    area = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    return area * 0.5


def ring_area(points) -> float:
    return abs(signed_area(points))


def oriented(points) -> list[tuple[float, float]]:
    """Return the ring with a positive orientation (union-friendly winding)."""
    pts = [(float(x), float(y)) for x, y in points]
    if signed_area(pts) < 0:
        pts.reverse()
    return pts


def arc_segments(radius: float, tol: float = FLATTEN_TOL) -> int:
    """Segment count for a full circle of ``radius`` with bounded sagitta."""
    r = max(abs(radius), 1e-6)
    # sagitta ~= r * theta^2 / 8  ->  theta = sqrt(8 * tol / r)
    step = math.sqrt(8.0 * tol / r)
    step = min(max(step, math.radians(6.0)), math.radians(90.0))
    return max(8, int(math.ceil(2.0 * math.pi / step)))


def arc_cubics(cx: float, cy: float, r: float, a0: float, a1: float):
    """Yield ``(c1x, c1y, c2x, c2y, x, y)`` cubics approximating an arc.

    ``a0``/``a1`` are degrees in screen space: 0 deg points +x (east),
    90 deg points +y (south), i.e. angles grow clockwise on screen.
    """
    span = a1 - a0
    pieces = max(1, int(math.ceil(abs(span) / 90.0)))
    step = span / pieces
    k = KAPPA * (abs(step) / 90.0)
    for i in range(pieces):
        b0 = math.radians(a0 + step * i)
        b1 = math.radians(a0 + step * (i + 1))
        x0, y0 = cx + r * math.cos(b0), cy + r * math.sin(b0)
        x1, y1 = cx + r * math.cos(b1), cy + r * math.sin(b1)
        t0x, t0y = -math.sin(b0), math.cos(b0)      # tangent at b0
        t1x, t1y = -math.sin(b1), math.cos(b1)      # tangent at b1
        yield (x0 + k * r * t0x, y0 + k * r * t0y,
               x1 - k * r * t1x, y1 - k * r * t1y,
               x1, y1)


def circle(cx: float, cy: float, r: float) -> Path:
    """A full circle as four cubic arcs (positive orientation)."""
    path = Path()
    path.move_to(cx + r, cy)
    for cubic in arc_cubics(cx, cy, r, 0.0, 360.0):
        path.cubic_to(*cubic)
    return path.close()


def arc(cx: float, cy: float, r: float, a0: float, a1: float) -> Path:
    """An open arc path (no closing segment) from ``a0`` to ``a1`` degrees."""
    path = Path()
    x0 = cx + r * math.cos(math.radians(a0))
    y0 = cy + r * math.sin(math.radians(a0))
    path.move_to(x0, y0)
    for cubic in arc_cubics(cx, cy, r, a0, a1):
        path.cubic_to(*cubic)
    return path


def polygon(*points) -> Path:
    """A closed polygon from explicit unit-space points."""
    x0, y0 = points[0]
    path = Path().move_to(x0, y0)
    for x, y in points[1:]:
        path.line_to(x, y)
    return path.close()



def stadium(x0: float, y0: float, x1: float, y1: float, width: float,
            cap: str = "round") -> Path:
    """A capsule from ``(x0, y0)`` to ``(x1, y1)`` with the given width.

    ``cap="round"`` gives the usual capsule; ``cap="butt"`` gives flat ends
    (used by the resize shafts and the crosshair arms).
    """
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return circle(x0, y0, width * 0.5)
    ux, uy = dx / length, dy / length
    nx, ny = -uy * width * 0.5, ux * width * 0.5
    if cap == "butt":
        return polygon((x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                       (x1 - nx, y1 - ny), (x0 - nx, y0 - ny))
    half = width * 0.5
    a0 = math.degrees(math.atan2(ny, nx))
    path = Path().move_to(x0 + nx, y0 + ny)
    path.line_to(x1 + nx, y1 + ny)
    for cubic in arc_cubics(x1, y1, half, a0, a0 + 180.0):
        path.cubic_to(*cubic)
    path.line_to(x0 - nx, y0 - ny)
    for cubic in arc_cubics(x0, y0, half, a0 + 180.0, a0 + 360.0):
        path.cubic_to(*cubic)
    return path.close()


def rounded_rect(x0: float, y0: float, x1: float, y1: float,
                 radius: float) -> Path:
    """Axis-aligned rounded rectangle (radius clamped to half the short side)."""
    r = max(0.0, min(radius, abs(x1 - x0) * 0.5, abs(y1 - y0) * 0.5))
    if r <= 1e-9:
        return polygon((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    path = Path().move_to(x0 + r, y0)
    path.line_to(x1 - r, y0)
    for cubic in arc_cubics(x1 - r, y0 + r, r, -90.0, 0.0):
        path.cubic_to(*cubic)
    path.line_to(x1, y1 - r)
    for cubic in arc_cubics(x1 - r, y1 - r, r, 0.0, 90.0):
        path.cubic_to(*cubic)
    path.line_to(x0 + r, y1)
    for cubic in arc_cubics(x0 + r, y1 - r, r, 90.0, 180.0):
        path.cubic_to(*cubic)
    path.line_to(x0, y0 + r)
    for cubic in arc_cubics(x0 + r, y0 + r, r, 180.0, 270.0):
        path.cubic_to(*cubic)
    return path.close()


def annulus(cx: float, cy: float, r_out: float, r_in: float) -> list[Path]:
    """A ring: outer circle plus inner circle wound the other way (hole)."""
    outer = circle(cx, cy, r_out)
    inner = circle(cx, cy, r_in)
    inner = Path.from_points(reversed(flatten(inner)[0]))
    return [outer, inner]


def fillet(points, radius: float, radius_first: float | None = None) -> Path:
    """A closed polygon with circular corner fillets.

    ``radius`` applies to every corner; ``radius_first`` overrides the first
    one, which lets the arrow keep a nearly sharp tip while the rest of the
    silhouette stays softly rounded.
    """
    pts = [(float(x), float(y)) for x, y in points]
    n = len(pts)
    out = Path()
    for i in range(n):
        prev_pt = pts[(i - 1) % n]
        here = pts[i]
        next_pt = pts[(i + 1) % n]
        r = radius_first if (i == 0 and radius_first is not None) else radius
        v1x, v1y = prev_pt[0] - here[0], prev_pt[1] - here[1]
        v2x, v2y = next_pt[0] - here[0], next_pt[1] - here[1]
        l1, l2 = math.hypot(v1x, v1y), math.hypot(v2x, v2y)
        t1 = t2 = here
        arc_center = None
        rr = 0.0
        if l1 > 1e-12 and l2 > 1e-12 and r > 1e-9:
            u1x, u1y = v1x / l1, v1y / l1
            u2x, u2y = v2x / l2, v2y / l2
            cos_theta = max(-1.0, min(1.0, u1x * u2x + u1y * u2y))
            theta = math.acos(cos_theta)
            if 1e-6 < theta < math.pi - 1e-6:
                t = min(r / math.tan(theta * 0.5), l1 * 0.5, l2 * 0.5)
                rr = t * math.tan(theta * 0.5)
                t1 = (here[0] + u1x * t, here[1] + u1y * t)
                t2 = (here[0] + u2x * t, here[1] + u2y * t)
                bx, by = u1x + u2x, u1y + u2y
                bl = math.hypot(bx, by)
                if bl > 1e-12:
                    d = rr / math.sin(theta * 0.5)
                    arc_center = (here[0] + bx / bl * d, here[1] + by / bl * d)
        if i == 0:
            out.move_to(*t1)
        else:
            out.line_to(*t1)
        if arc_center is not None:
            a0 = math.degrees(math.atan2(t1[1] - arc_center[1],
                                         t1[0] - arc_center[0]))
            a1 = math.degrees(math.atan2(t2[1] - arc_center[1],
                                         t2[0] - arc_center[0]))
            span = (a1 - a0) % 360.0
            if span > 180.0:
                span -= 360.0
            for cubic in arc_cubics(arc_center[0], arc_center[1], rr,
                                    a0, a0 + span):
                out.cubic_to(*cubic)
        out.line_to(*t2)
    return out.close()




# --------------------------------------------------------------------------
# Flattening
# --------------------------------------------------------------------------

def _flatten_cubic(out, x0, y0, x1, y1, x2, y2, x3, y3, tol, depth=0):
    """Recursive de Casteljau subdivision with a flatness test."""
    dx, dy = x3 - x0, y3 - y0
    chord = math.hypot(dx, dy)
    d1 = abs((x1 - x0) * dy - (y1 - y0) * dx)
    d2 = abs((x2 - x0) * dy - (y2 - y0) * dx)
    if depth >= _MAX_SUBDIV or max(d1, d2) <= tol * max(chord, 1e-9):
        if chord > 1e-9 or out[-1] != (x3, y3):
            out.append((x3, y3))
        return
    ax, ay = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    bx, by = (x1 + x2) * 0.5, (y1 + y2) * 0.5
    cx, cy = (x2 + x3) * 0.5, (y2 + y3) * 0.5
    dx1, dy1 = (ax + bx) * 0.5, (ay + by) * 0.5
    dx2, dy2 = (bx + cx) * 0.5, (by + cy) * 0.5
    mx, my = (dx1 + dx2) * 0.5, (dy1 + dy2) * 0.5
    _flatten_cubic(out, x0, y0, ax, ay, dx1, dy1, mx, my, tol, depth + 1)
    _flatten_cubic(out, mx, my, dx2, dy2, cx, cy, x3, y3, tol, depth + 1)


def flatten(path: Path, tol: float = FLATTEN_TOL):
    """Flatten one subpath to ``(points, closed)`` in unit space.

    Exactly one ``move_to`` is expected per Path (shapes use separate Path
    objects for disjoint pieces), which keeps this function simple and keeps
    the SVG emitter honest.
    """
    pts: list[tuple[float, float]] = []
    cur: tuple[float, float] | None = None
    start: tuple[float, float] | None = None
    closed = False
    for seg in path.segments:
        kind = seg[0]
        if kind == "M":
            if cur is not None:
                raise ValueError("flatten() expects a single move_to per Path")
            cur = start = (seg[1], seg[2])
            pts.append(cur)
            continue
        if cur is None:
            raise ValueError("path segment before move_to")
        if kind == "L":
            cur = (seg[1], seg[2])
            pts.append(cur)
        elif kind == "Q":
            cx, cy, ex, ey = seg[1], seg[2], seg[3], seg[4]
            x0, y0 = cur
            # elevate the quadratic to a cubic (exactly equivalent)
            c1x = x0 + (2.0 / 3.0) * (cx - x0)
            c1y = y0 + (2.0 / 3.0) * (cy - y0)
            c2x = ex + (2.0 / 3.0) * (cx - ex)
            c2y = ey + (2.0 / 3.0) * (cy - ey)
            _flatten_cubic(pts, x0, y0, c1x, c1y, c2x, c2y, ex, ey, tol)
            cur = (ex, ey)
        elif kind == "C":
            _flatten_cubic(pts, cur[0], cur[1], seg[1], seg[2], seg[3], seg[4],
                           seg[5], seg[6], tol)
            cur = (seg[5], seg[6])
        elif kind == "Z":
            closed = True
            if start is not None:
                pts.append(start)
                cur = start
        else:                                    # pragma: no cover - guard
            raise ValueError(f"unknown segment {kind!r}")
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts, closed


# --------------------------------------------------------------------------
# Stroke -> outline
# --------------------------------------------------------------------------

def stroke_outline(path: Path, width: float, cap: str = "round",
                   join: str = "round") -> list[Path]:
    """Convert a centre line into fillable outline rings ("stroke as fill").

    Returns one quad per segment plus one disc per joint; every ring is wound
    the same way so a nonzero fill yields the union of the pieces.
    """
    if width <= 0.0:
        return []
    points, closed = flatten(path)
    if len(points) < 2:
        if len(points) == 1 and cap == "round":
            return [Path.from_points(oriented_circle(points[0], width * 0.5))]
        return []
    hw = width * 0.5
    rings: list[Path] = []
    count = len(points) if closed else len(points) - 1
    for i in range(count):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % len(points)]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length <= 1e-12:
            continue
        nx, ny = -dy / length * hw, dx / length * hw
        rings.append(Path.from_points(oriented(
            ((x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
             (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)))))
    if join == "round":
        first = 0 if closed else 1
        last = len(points) if closed else len(points) - 1
        for i in range(first, last):
            rings.append(Path.from_points(oriented_circle(points[i], hw)))
    if cap == "round" and not closed:
        rings.append(Path.from_points(oriented_circle(points[0], hw)))
        rings.append(Path.from_points(oriented_circle(points[-1], hw)))
    return rings


def oriented_circle(centre, radius: float) -> list[tuple[float, float]]:
    """A circle as a polyline with positive orientation."""
    steps = arc_segments(radius)
    cx, cy = centre
    return oriented([(cx + radius * math.cos(2.0 * math.pi * i / steps),
                      cy + radius * math.sin(2.0 * math.pi * i / steps))
                     for i in range(steps)])


# --------------------------------------------------------------------------
# Rasterisation
# --------------------------------------------------------------------------

def rasterize(rings, size: int, fill_rule: str = "nonzero",
              ss: int = SS) -> list[float]:
    """Per-pixel coverage (0..1) of ``rings`` (iterables of unit-space points).

    Renders on a ``size * ss`` square supersample grid and averages each
    ``ss x ss`` block.  Vertices use the half-open rule ``y0 <= y < y1`` so a
    crossing is never counted twice.
    """
    grid = size * ss
    edges = []
    for pts in rings:
        n = len(pts)
        if n < 3:
            continue
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            x0 *= grid
            y0 *= grid
            x1 *= grid
            y1 *= grid
            if y0 == y1:
                continue
            if y0 < y1:
                edges.append((x0, y0, x1, y1, 1))
            else:
                edges.append((x1, y1, x0, y0, -1))
    counts = [0] * (size * size)
    for sy in range(grid):
        yc = sy + 0.5
        crossings = []
        for x0, y0, x1, y1, direction in edges:
            if y0 <= yc < y1:
                crossings.append((x0 + (yc - y0) * (x1 - x0) / (y1 - y0),
                                  direction))
        if not crossings:
            continue
        crossings.sort()
        spans = []
        if fill_rule == "evenodd":
            for i in range(0, len(crossings) - 1, 2):
                spans.append((crossings[i][0], crossings[i + 1][0]))
        else:
            wind = 0
            start = 0.0
            for x, direction in crossings:
                if wind == 0:
                    start = x
                wind += direction
                if wind == 0:
                    spans.append((start, x))
        if not spans:
            continue
        row = sy // ss
        base = row * size
        for xa, xb in spans:
            if xb <= xa:
                continue
            sa = max(0, int(math.ceil(xa - 0.5)))
            sb = min(grid, int(math.ceil(xb - 0.5)))
            if sb <= sa:
                continue
            for col in range(sa // ss, (sb - 1) // ss + 1):
                lo = col * ss if col * ss > sa else sa
                hi = (col + 1) * ss if (col + 1) * ss < sb else sb
                if hi > lo:
                    counts[base + col] += hi - lo
    scale = 1.0 / (ss * ss)
    return [c * scale for c in counts]




# --------------------------------------------------------------------------
# Blur / shift helpers (used by the drop shadow)
# --------------------------------------------------------------------------

def box_blur(plane, size: int, radius: int, passes: int = 2) -> list[float]:
    """Separable box blur on a ``size x size`` float plane.

    Two passes approximate a Gaussian closely enough for a soft drop shadow,
    and the operation is fully deterministic (integer window sums).
    """
    if radius <= 0:
        return list(plane)
    data = list(plane)
    window = float(2 * radius + 1)
    for _ in range(passes):
        # horizontal pass
        out = [0.0] * (size * size)
        for y in range(size):
            row = y * size
            total = 0.0
            for x in range(-radius, radius + 1):
                if 0 <= x < size:
                    total += data[row + x]
            for x in range(size):
                out[row + x] = total / window
                add = x + radius + 1
                rem = x - radius
                if add < size:
                    total += data[row + add]
                if 0 <= rem:
                    total -= data[row + rem]
        # vertical pass
        data = out
        out = [0.0] * (size * size)
        for x in range(size):
            total = 0.0
            for y in range(-radius, radius + 1):
                if 0 <= y < size:
                    total += data[y * size + x]
            for y in range(size):
                out[y * size + x] = total / window
                add = y + radius + 1
                rem = y - radius
                if add < size:
                    total += data[add * size + x]
                if 0 <= rem:
                    total -= data[rem * size + x]
        data = out
    return data


def shift_plane(plane, size: int, dx: int, dy: int) -> list[float]:
    """Translate a coverage plane by whole pixels (clipped to the canvas)."""
    if dx == 0 and dy == 0:
        return list(plane)
    out = [0.0] * (size * size)
    for y in range(size):
        sy = y - dy
        if sy < 0 or sy >= size:
            continue
        src_row = sy * size
        dst_row = y * size
        for x in range(size):
            sx = x - dx
            if 0 <= sx < size:
                out[dst_row + x] = plane[src_row + sx]
    return out


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

class Canvas:
    """Float RGBA canvas (straight alpha, source-over) of any width x height."""

    __slots__ = ("width", "height", "data")

    def __init__(self, width: int, height: int | None = None):
        self.width = width
        self.height = width if height is None else height
        self.data = [0.0] * (self.width * self.height * 4)

    def over(self, coverage, rgb, alpha: float = 1.0,
             offset: tuple[int, int] = (0, 0)) -> None:
        """Composite a coverage plane in ``rgb`` at ``alpha`` over the canvas.

        ``coverage`` must match the canvas dimensions (the renderer always
        rasterises at the exact cursor size, so no resampling happens).
        """
        if alpha <= 0.0:
            return
        width, height = self.width, self.height
        sr, sg, sb = rgb
        data = self.data
        dx, dy = offset
        for y in range(height):
            sy = y - dy
            if sy < 0 or sy >= height:
                continue
            src_row = sy * width
            dst_row = y * width * 4
            for x in range(width):
                sx = x - dx
                if sx < 0 or sx >= width:
                    continue
                cov = coverage[src_row + sx]
                if cov <= 0.0:
                    continue
                sa = cov * alpha
                i = dst_row + x * 4
                da = data[i + 3]
                oa = sa + da * (1.0 - sa)
                if oa <= 0.0:
                    continue
                w_src = sa / oa
                w_dst = da * (1.0 - sa) / oa
                data[i] = sr * w_src + data[i] * w_dst
                data[i + 1] = sg * w_src + data[i + 1] * w_dst
                data[i + 2] = sb * w_src + data[i + 2] * w_dst
                data[i + 3] = oa

    def fill_rect(self, x0: int, y0: int, w: int, h: int, rgb,
                  alpha: float = 1.0) -> None:
        """Opaque (or translucent) axis-aligned rectangle, for preview sheets."""
        width = self.width
        data = self.data
        r, g, b = rgb
        for y in range(max(0, y0), min(self.height, y0 + h)):
            row = y * width * 4
            for x in range(max(0, x0), min(width, x0 + w)):
                i = row + x * 4
                da = data[i + 3]
                oa = alpha + da * (1.0 - alpha)
                if oa <= 0.0:
                    continue
                w_src = alpha / oa
                w_dst = da * (1.0 - alpha) / oa
                data[i] = r * w_src + data[i] * w_dst
                data[i + 1] = g * w_src + data[i + 1] * w_dst
                data[i + 2] = b * w_src + data[i + 2] * w_dst
                data[i + 3] = oa



    def blit(self, x0: int, y0: int, side: int, rgba: bytes) -> None:
        """Composite a raw RGBA byte image (source-over, straight alpha)."""
        width, height = self.width, self.height
        data = self.data
        for y in range(side):
            dy = y0 + y
            if dy < 0 or dy >= height:
                continue
            src_row = y * side * 4
            dst_row = dy * width * 4
            for x in range(side):
                dx = x0 + x
                if dx < 0 or dx >= width:
                    continue
                si = src_row + x * 4
                sa = rgba[si + 3] / 255.0
                if sa <= 0.0:
                    continue
                i = dst_row + dx * 4
                da = data[i + 3]
                oa = sa + da * (1.0 - sa)
                w_src = sa / oa
                w_dst = da * (1.0 - sa) / oa
                data[i] = rgba[si] / 255.0 * w_src + data[i] * w_dst
                data[i + 1] = rgba[si + 1] / 255.0 * w_src + data[i + 1] * w_dst
                data[i + 2] = rgba[si + 2] / 255.0 * w_src + data[i + 2] * w_dst
                data[i + 3] = oa

    def to_bytes(self) -> bytes:
        """Row-major, top-to-bottom 8-bit RGBA."""
        out = bytearray(len(self.data))
        for i, value in enumerate(self.data):
            if value <= 0.0:
                out[i] = 0
            elif value >= 1.0:
                out[i] = 255
            else:
                out[i] = int(value * 255.0 + 0.5)
        return bytes(out)


# --------------------------------------------------------------------------
# Cursor parts / strokes and the layer renderer
# --------------------------------------------------------------------------

#: Outline stroke width in unit space: 1.5 px at 32 px, scaled with the size
#: (1.125 px at 24 px, 2.25 px at 48 px, 3 px at 64 px).
OUTLINE_WIDTH = 1.5 / 32.0


class Part:
    """A filled piece of a cursor that the renderer also outlines.

    All outlines are painted *before* any fill, so overlapping parts merge into
    one silhouette whose outline only shows on the outside.  A part is normally
    one ``Path``; ``Part.from_rings`` accepts an already stroked ring set (used
    for glyphs such as the question mark).
    """

    __slots__ = ("path", "rings", "role", "outline", "alpha", "min_size")

    def __init__(self, path: Path | None = None, role: str = "body",
                 outline: bool = True, alpha: float = 1.0, min_size: int = 0,
                 rings=None):
        if (path is None) == (rings is None):
            raise ValueError("a Part needs exactly one of path/rings")
        self.path = path
        self.rings = list(rings) if rings is not None else None
        self.role = role
        self.outline = outline
        self.alpha = alpha
        self.min_size = min_size

    @classmethod
    def from_rings(cls, rings, role: str = "body", outline: bool = True,
                   alpha: float = 1.0, min_size: int = 0) -> "Part":
        return cls(None, role, outline, alpha, min_size, rings=rings)


class Stroke:
    """A stroked centre line (plus/minus glyph bars, arcs, refraction glints)."""

    __slots__ = ("path", "width", "role", "alpha", "min_size", "cap", "join")

    def __init__(self, path: Path, width: float, role: str = "accent",
                 alpha: float = 1.0, min_size: int = 0,
                 cap: str = "round", join: str = "round"):
        self.path = path
        self.width = width
        self.role = role
        self.alpha = alpha
        self.min_size = min_size
        self.cap = cap
        self.join = join


def build_layers(parts, strokes, outline_width: float = OUTLINE_WIDTH):
    """Group parts/strokes into paint layers.

    Returns ``(layers, silhouette)`` where ``layers`` maps a role name to a
    list of ``(rings, alpha, min_size)`` tuples and ``silhouette`` is the union
    of every part (used for the drop shadow).
    """
    layers: dict[str, list] = {role: [] for role in ROLE_ORDER}
    silhouette: list[list[tuple[float, float]]] = []
    for part in parts:
        if part.rings is not None:
            part_rings = [oriented(flatten(ring)[0]) for ring in part.rings]
            part_rings = [r for r in part_rings if len(r) >= 3]
            if not part_rings:
                continue
            silhouette.extend(part_rings)
            if part.outline:
                outline_rings = []
                for ring in part_rings:
                    outline_rings.extend(
                        stroke_outline(Path.from_points(ring), outline_width))
                layers["outline"].append(
                    ([oriented(flatten(r)[0]) for r in outline_rings], 1.0,
                     part.min_size))
            layers[part.role].append((part_rings, part.alpha, part.min_size))
            continue
        points, _ = flatten(part.path)
        if len(points) < 3:
            continue
        ring = oriented(points)
        silhouette.append(ring)
        if part.outline:
            rings = [oriented(flatten(outline_ring)[0])
                     for outline_ring in stroke_outline(part.path, outline_width)]
            layers["outline"].append((rings, 1.0, part.min_size))
        layers[part.role].append(([ring], part.alpha, part.min_size))
    for stroke in strokes:
        rings = [oriented(flatten(ring)[0])
                 for ring in stroke_outline(stroke.path, stroke.width,
                                            cap=stroke.cap, join=stroke.join)]
        if not rings:
            continue
        layers[stroke.role].append((rings, stroke.alpha, stroke.min_size))
    return layers, silhouette


def render(parts, strokes, size: int, palette, ss: int = SS,
           shadow: bool = True, outline_width: float = OUTLINE_WIDTH) -> bytes:
    """Render one cursor image and return 8-bit RGBA bytes.

    ``palette`` is a mapping with the keys ``body``, ``outline``, ``accent``,
    ``danger``, ``refract`` and ``shadow`` (hex strings).
    """
    layers, silhouette = build_layers(parts, strokes, outline_width)
    canvas = Canvas(size)
    if shadow and size >= SHADOW_MIN_SIZE and silhouette:
        coverage = rasterize(silhouette, size, ss=ss)
        radius = max(1, int(round(SHADOW_RADIUS_RATIO * size)))
        coverage = box_blur(coverage, size, radius, passes=2)
        offset = (int(round(SHADOW_OFFSET_UNITS[0] * size)),
                  int(round(SHADOW_OFFSET_UNITS[1] * size)))
        coverage = shift_plane(coverage, size, *offset)
        canvas.over(coverage, parse_hex_rgb(palette["shadow"]), SHADOW_ALPHA)
    for role in ROLE_ORDER:
        rgb = parse_hex_rgb(palette[role])
        for rings, alpha, min_size in layers[role]:
            if not rings or (min_size and size < min_size):
                continue
            canvas.over(rasterize(rings, size, ss=ss), rgb, alpha)
    return canvas.to_bytes()


def preview_sheet(cells, cell: int, columns: int, pad: int,
                  background=("#08090B", "#F3F5F8")) -> tuple[int, int, Canvas]:
    """Compose a contact sheet of pre-rendered RGBA cells.

    ``cells`` is a list of ``(rgba, side)`` tuples in reading order; the cell
    background alternates between the two ``background`` colours so every
    cursor is judged against both a dark and a light backdrop.
    """
    rows = (len(cells) + columns - 1) // columns
    width = columns * (cell + pad) + pad
    height = rows * (cell + pad) + pad
    canvas = Canvas(width, height)
    dark = parse_hex_rgb(background[0])
    light = parse_hex_rgb(background[1])
    for index, (rgba, side) in enumerate(cells):
        col = index % columns
        row = index // columns
        x0 = pad + col * (cell + pad)
        y0 = pad + row * (cell + pad)
        rgb = dark if (col + row) % 2 == 0 else light
        canvas.fill_rect(x0, y0, cell, cell, rgb, 1.0)
        canvas.blit(x0 + (cell - side) // 2, y0 + (cell - side) // 2, side, rgba)
    return width, height, canvas
