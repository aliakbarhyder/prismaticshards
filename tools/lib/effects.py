"""Post-processing passes for the Prismatic Shards artwork tools.

Blur is the diffuser that turns hard shard edges into glass; noise is the
dither that keeps wide gradients from banding. Both are written to keep the
inner loops inside C (`itertools.accumulate` over a row or column), because a
4K wallpaper is a lot of pixels for a Python `for` statement.

Development tooling only — not part of the installed theme.
"""

from __future__ import annotations

from itertools import accumulate

from .canvas import Canvas


def box_blur(canvas: Canvas, radius: int = 2, passes: int = 1) -> Canvas:
    """Separable box blur. Three passes approximate a Gaussian closely enough."""
    if radius <= 0:
        return canvas
    for _ in range(passes):
        _blur_rows(canvas, radius)
        _blur_columns(canvas, radius)
    return canvas


def _blur_rows(canvas: Canvas, radius: int):
    w, h, c = canvas.w, canvas.h, canvas.channels
    for y in range(h):
        start, end = y * w * c, (y + 1) * w * c
        row = canvas.buf[start:end]
        for ch in range(c):
            prefix = [0] + list(accumulate(row[ch::c]))
            out = bytearray(w)
            for x in range(w):
                lo = x - radius
                hi = x + radius
                lo = 0 if lo < 0 else lo
                hi = w - 1 if hi > w - 1 else hi
                # Divide by the pixels actually inside the clamped window, not
                # by the nominal window: at the borders the window is shorter,
                # and dividing by `window` there would darken the first/last
                # column to about two thirds of its value.
                out[x] = (prefix[hi + 1] - prefix[lo]) // (hi - lo + 1)
            row[ch::c] = bytes(out)
        canvas.buf[start:end] = bytes(row)


def _blur_columns(canvas: Canvas, radius: int):
    w, h, c = canvas.w, canvas.h, canvas.channels
    buf = canvas.buf
    for ch in range(c):
        for x in range(w):
            prefix = [0] + list(accumulate(buf[(y * w + x) * c + ch] for y in range(h)))
            out = bytearray(h)
            for y in range(h):
                lo = y - radius
                hi = y + radius
                lo = 0 if lo < 0 else lo
                hi = h - 1 if hi > h - 1 else hi
                # Same clamp-aware divisor as the row pass; see `_blur_rows`.
                out[y] = (prefix[hi + 1] - prefix[lo]) // (hi - lo + 1)
            for y in range(h):
                buf[(y * w + x) * c + ch] = out[y]


def depth_of_field(canvas: Canvas, focus_radius: float, centre, radius: int = 3, passes: int = 1):
    """Blur everything outside a soft circular focus region.

    Used by the wallpapers so the shards closest to the "light source" stay
    sharp while the rest of the glass dissolves — a small amount of depth
    keeps a very dark wallpaper from reading as flat.
    """
    blurred = Canvas(canvas.w, canvas.h, canvas.channels)
    blurred.buf[:] = canvas.buf[:]
    box_blur(blurred, radius, passes)

    cx, cy = centre
    c = canvas.channels
    for y in range(canvas.h):
        dy = y - cy
        for x in range(canvas.w):
            dx = x - cx
            d = (dx * dx + dy * dy) ** 0.5
            if d <= focus_radius:
                continue
            t = (d - focus_radius) / max(1.0, focus_radius)
            t = 1.0 if t > 1 else t
            base = (y * canvas.w + x) * c
            for ch in range(3):
                sharp = canvas.buf[base + ch]
                soft = blurred.buf[base + ch]
                canvas.buf[base + ch] = int(sharp + (soft - sharp) * t)
    return canvas


def add_noise(canvas: Canvas, amount: int = 3, seed: int = 1234567) -> Canvas:
    """Deterministic dither. Same seed, same wallpaper, byte for byte."""
    state = seed & 0xFFFFFFFF
    buf = canvas.buf
    c = canvas.channels
    for i in range(0, len(buf), c):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        n = ((state >> 16) % (2 * amount + 1)) - amount
        for ch in range(3):
            v = buf[i + ch] + n
            buf[i + ch] = 0 if v < 0 else (255 if v > 255 else v)
    return canvas


def vignette(canvas: Canvas, strength: float = 0.35, power: float = 2.4) -> Canvas:
    cx, cy = canvas.w / 2.0, canvas.h / 2.0
    max_d = (cx * cx + cy * cy) ** 0.5
    c = canvas.channels
    for y in range(canvas.h):
        row = canvas.buf[canvas._row_slice(y)]
        dy = y - cy
        for x in range(canvas.w):
            dx = x - cx
            d = ((dx * dx + dy * dy) ** 0.5) / max_d
            factor = 1.0 - strength * (d ** power)
            base = x * c
            for ch in range(3):
                row[base + ch] = int(row[base + ch] * factor)
        canvas.buf[canvas._row_slice(y)] = row
    return canvas


def composite(canvas: Canvas, top: Canvas, alpha: float = 1.0) -> Canvas:
    """Source-over blit of another canvas (its alpha channel is respected)."""
    if (top.w, top.h) != (canvas.w, canvas.h):
        raise ValueError("canvas sizes must match")
    c_dst, c_src = canvas.channels, top.channels
    for i in range(canvas.w * canvas.h):
        s = i * c_src
        d = i * c_dst
        src_alpha = (top.buf[s + 3] / 255.0 if c_src == 4 else 1.0) * alpha
        if src_alpha <= 0.002:
            continue
        for ch in range(3):
            dv = canvas.buf[d + ch]
            sv = top.buf[s + ch]
            canvas.buf[d + ch] = int(dv + (sv - dv) * src_alpha)
    return canvas
