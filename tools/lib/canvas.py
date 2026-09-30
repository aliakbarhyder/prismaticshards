"""A tiny raster canvas used to author Prismatic Shards wallpapers and previews.

Development tooling only — nothing here ships with the theme. The point of
writing it by hand is that the artwork is *original and reproducible*: every
pixel in `backgrounds/`, `preview.png` and `assets/previews/` comes out of
these lines, so anyone can regenerate, retune or resize it.

Design notes
------------
* Buffers are 8-bit RGB or RGBA `bytearray`s, one flat allocation.
* Rows are manipulated as slices wherever possible; per-pixel Python loops
  only run for coverage tests, and the heavy passes (blur) use
  `itertools.accumulate` so the inner loop is C code.
* Blending is plain source-over in sRGB. Gamma-accurate compositing would be
  more correct, but the artwork is authored in this space and looks the way it
  was designed to look.
"""

from __future__ import annotations

import math
from itertools import accumulate


def hex_to_rgb(value: str):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c0, c1, t: float):
    """Blend two colours. Returns ints so results can be written straight to a buffer."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return tuple(int(round(lerp(c0[i], c1[i], t))) for i in range(len(c0)))


def gradient_stops(stops, t: float):
    """Sample a list of (position, colour) pairs at t."""
    if t <= stops[0][0]:
        return tuple(stops[0][1])
    if t >= stops[-1][0]:
        return tuple(stops[-1][1])
    for i in range(1, len(stops)):
        pos, colour = stops[i]
        prev_pos, prev_colour = stops[i - 1]
        if t <= pos:
            local = 0.0 if pos == prev_pos else (t - prev_pos) / (pos - prev_pos)
            return mix(prev_colour, colour, local)
    return tuple(stops[-1][1])


class Canvas:
    """A small RGB/RGBA canvas with gradient, polygon and blur primitives."""

    def __init__(self, width: int, height: int, channels: int = 3, background=(0, 0, 0)):
        self.w = width
        self.h = height
        self.channels = channels
        self.buf = bytearray(width * height * channels)
        if channels == 3:
            self.fill_rgb(background)
        else:
            self.fill_rgba((background[0], background[1], background[2], 255))

    # ------------------------------------------------------------------ fills

    def fill_rgb(self, colour):
        self.buf[:] = bytes(colour[:3]) * (self.w * self.h)
        return self

    def fill_rgba(self, colour):
        self.buf[:] = bytes(colour[:4]) * (self.w * self.h)
        return self

    def _row_slice(self, y: int) -> slice:
        c = self.channels
        return slice(y * self.w * c, (y + 1) * self.w * c)

    # -------------------------------------------------------------- gradients

    def linear_gradient(self, p0, p1, stops):
        """Fill the canvas with a linear gradient from p0 to p1."""
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        denominator = dx * dx + dy * dy
        if denominator == 0:
            raise ValueError("gradient endpoints must differ")

        lut = [gradient_stops(stops, i / 255.0) for i in range(256)]
        c = self.channels

        for y in range(self.h):
            # t varies linearly along the row, so only the two ends need work.
            t_row = ((0 - p0[0]) * dx + (y - p0[1]) * dy) / denominator
            t_step = dx / denominator
            row = bytearray(self.w * c)
            for x in range(self.w):
                t = t_row + t_step * x
                idx = 0 if t <= 0 else (255 if t >= 1 else int(t * 255))
                colour = lut[idx]
                base = x * c
                row[base] = colour[0]
                row[base + 1] = colour[1]
                row[base + 2] = colour[2]
                if c == 4:
                    row[base + 3] = 255
            self.buf[self._row_slice(y)] = row
        return self

    def radial_glow(self, centre, radius: float, colour, alpha: float = 1.0, falloff: float = 2.0):
        """Add a soft additive glow falling off as (1 - d/r)^falloff."""
        cx, cy = centre
        r2 = radius * radius
        c = self.channels
        for y in range(self.h):
            dy = y - cy
            if dy * dy > r2:
                continue
            row = self.buf[self._row_slice(y)]
            for x in range(self.w):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                w = (1.0 - math.sqrt(d2) / radius) ** falloff * alpha
                if w <= 0.002:
                    continue
                base = x * c
                for ch in range(3):
                    v = row[base + ch] + colour[ch] * w
                    row[base + ch] = 255 if v > 255 else int(v)
            self.buf[self._row_slice(y)] = row
        return self

    # --------------------------------------------------------------- polygons

    @staticmethod
    def _polygon_spans(points, y: float):
        """Return sorted x-intercepts of a polygon at scanline y (even-odd)."""
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if y0 == y1:
                continue
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        return xs

    def fill_polygon(self, points, colour, alpha: float = 1.0):
        """Fill a polygon (list of (x, y)) with straight alpha blending."""
        if alpha <= 0:
            return self
        min_y = max(0, int(math.floor(min(p[1] for p in points))))
        max_y = min(self.h - 1, int(math.ceil(max(p[1] for p in points))))
        c = self.channels
        for y in range(min_y, max_y + 1):
            xs = self._polygon_spans(points, y + 0.5)
            if len(xs) < 2:
                continue
            row = self.buf[self._row_slice(y)]
            for i in range(0, len(xs) - 1, 2):
                x_start = max(0, int(math.floor(xs[i])))
                x_end = min(self.w - 1, int(math.ceil(xs[i + 1])))
                for x in range(x_start, x_end + 1):
                    base = x * c
                    for ch in range(3):
                        dst = row[base + ch]
                        row[base + ch] = int(dst + (colour[ch] - dst) * alpha)
            self.buf[self._row_slice(y)] = row
        return self

    def fill_gradient_polygon(self, points, stops, axis, alpha_fn=None):
        """Fill a polygon with a gradient along `axis` ((ax, ay), (bx, by)).

        `alpha_fn(t)` returns the alpha at gradient position t, which is how a
        shard's refracted edge fades out along its length.
        """
        (ax, ay), (bx, by) = axis
        dx, dy = bx - ax, by - ay
        denominator = dx * dx + dy * dy
        if denominator == 0:
            raise ValueError("gradient axis must have length")
        min_y = max(0, int(math.floor(min(p[1] for p in points))))
        max_y = min(self.h - 1, int(math.ceil(max(p[1] for p in points))))
        c = self.channels
        for y in range(min_y, max_y + 1):
            xs = self._polygon_spans(points, y + 0.5)
            if len(xs) < 2:
                continue
            row = self.buf[self._row_slice(y)]
            for i in range(0, len(xs) - 1, 2):
                x_start = max(0, int(math.floor(xs[i])))
                x_end = min(self.w - 1, int(math.ceil(xs[i + 1])))
                for x in range(x_start, x_end + 1):
                    t = ((x - ax) * dx + (y - ay) * dy) / denominator
                    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                    colour = gradient_stops(stops, t)
                    alpha = alpha_fn(t) if alpha_fn else 1.0
                    if alpha <= 0.002:
                        continue
                    base = x * c
                    for ch in range(3):
                        dst = row[base + ch]
                        row[base + ch] = int(dst + (colour[ch] - dst) * alpha)
            self.buf[self._row_slice(y)] = row
        return self

    def scale_polygon(self, unit_points):
        """Map normalised (0..1) coordinates onto the canvas."""
        return [(x * self.w, y * self.h) for (x, y) in unit_points]

    def fill_unit_polygon(self, unit_points, colour, alpha=1.0):
        return self.fill_polygon(self.scale_polygon(unit_points), colour, alpha)

    def fill_unit_gradient_polygon(self, unit_points, stops, unit_axis, alpha_fn=None):
        (ax, ay), (bx, by) = unit_axis
        axis = ((ax * self.w, ay * self.h), (bx * self.w, by * self.h))
        return self.fill_gradient_polygon(self.scale_polygon(unit_points), stops, axis, alpha_fn)

    # ---------------------------------------------------------------- shapes

    def fill_rect(self, x, y, w, h, colour, alpha=1.0):
        return self.fill_polygon(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], colour, alpha
        )

    def fill_rounded_rect(self, x, y, w, h, radius, colour, alpha=1.0, steps=10):
        radius = min(radius, w / 2, h / 2)
        points = []
        corners = (
            (x + w - radius, y + radius, -math.pi / 2, 0.0),
            (x + w - radius, y + h - radius, 0.0, math.pi / 2),
            (x + radius, y + h - radius, math.pi / 2, math.pi),
            (x + radius, y + radius, math.pi, 3 * math.pi / 2),
        )
        for cx, cy, a0, a1 in corners:
            for i in range(steps + 1):
                angle = a0 + (a1 - a0) * (i / steps)
                points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return self.fill_polygon(points, colour, alpha)

    def stroke_line(self, p0, p1, width, colour, alpha=1.0):
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            return self
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        quad = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
        return self.fill_polygon(quad, colour, alpha)

    def stroke_unit_line(self, p0, p1, width, colour, alpha=1.0, width_scale=None):
        scale = width_scale if width_scale is not None else self.h
        return self.stroke_line(
            (p0[0] * self.w, p0[1] * self.h),
            (p1[0] * self.w, p1[1] * self.h),
            width * scale,
            colour,
            alpha,
        )
