#!/usr/bin/env python3
"""Generate the Prismatic Shards wallpapers.

Every wallpaper in `backgrounds/` (dark) and `variants/light/backgrounds/`
(light) is produced by this script. Nothing is downloaded and nothing is
traced from a photograph: a fractured-glass surface is generated from a fixed
seed, lit from one corner, and only a handful of its edges refract.

The metaphor is literal here, which is the point. A sheet of glass is
triangulated into shards; almost all of it stays graphite; the light that hits
it splits into blue, cyan, violet, magenta and pink along a few edges only.

Usage
-----
    python3 tools/wallpapers.py --mode dark --size 2560x1440
    python3 tools/wallpapers.py --mode light --size 2560x1440
    python3 tools/wallpapers.py --mode both
    python3 tools/wallpapers.py --mode dark --render-size 960x540 --format png --only obsidian

Rendering happens at `--render-size` and the shipped resolution is reached with
macOS `sips` when available (smooth resampling of a smooth image). On Linux,
pass `--render-size` equal to `--size` and the PNG is written directly, or
resample with any image tool you already have. A 2560x1440 render takes about
fifteen seconds per design; a 960x540 one takes about two.

Development tooling only: the installed theme ships finished images and never
runs Python.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import effects, png  # noqa: E402
from lib.canvas import Canvas, hex_to_rgb, mix  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TAU = 2.0 * math.pi


class Rng:
    """Tiny deterministic LCG. Same seed, same wallpaper, byte for byte."""

    def __init__(self, seed: int):
        self.state = seed & 0x7FFFFFFF

    def next(self) -> float:
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF

    def between(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.next()


# Where the light comes from, in normalised coordinates. Every design places
# its glow, its facet shading and its brightest refraction along this one point,
# which is what keeps a random-looking field from reading as random.
LIGHT_ORIGIN = (0.76, 0.14)

DARK = {
    "name": "dark",
    "background": "#08090B",
    "surface": "#11151A",
    "graphite": "#1E2530",
    "elevated": "#171B22",
    "corner": "#040508",
    "shard_far": "#090C10",
    "shard_near": "#222C3A",
    "accents": ("#63D7FF", "#4DA3FF", "#8B7CFF", "#C77DFF", "#F2A7D8"),
    "core": "#C6D2E4",
    "shard_alpha": 0.88,
    "edge_alpha": 0.80,
    "glow": 0.34,
    "noise": 2,
    "vignette": 0.38,
    "light": LIGHT_ORIGIN,
}

LIGHT = {
    "name": "light",
    "background": "#F4F6F9",
    "surface": "#FFFFFF",
    "graphite": "#D9DFE8",
    "elevated": "#FFFFFF",
    "corner": "#DFE5EE",
    "shard_far": "#D5DDE8",
    "shard_near": "#FCFDFF",
    "accents": ("#009FCF", "#1677FF", "#705FE8", "#B86BD6", "#D889BA"),
    "core": "#46536B",
    "shard_alpha": 0.62,
    "edge_alpha": 0.50,
    "glow": 0.14,
    "noise": 2,
    "vignette": 0.10,
    "light": LIGHT_ORIGIN,
}

PALETTES = {"dark": DARK, "light": LIGHT}


def unit_to_px(canvas: Canvas, point):
    return (point[0] * canvas.w, point[1] * canvas.h)


def gradient_stroke(canvas: Canvas, p0, p1, width: float, stops, alpha_fn=None, alpha: float = 1.0):
    """Draw a line whose colour and opacity change along its length.

    A straight alpha line reads as a neon tube. Refracted light is brightest
    where it leaves the shard and fades to nothing at the other end, which is
    what `alpha_fn` describes.
    """
    x0, y0 = unit_to_px(canvas, p0)
    x1, y1 = unit_to_px(canvas, p1)
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1.0:
        return canvas
    half = width * canvas.h / 2
    nx, ny = -dy / length * half, dx / length * half

    quad = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    scaled = (lambda t: alpha_fn(t) * alpha) if alpha_fn else (lambda _t: alpha)
    return canvas.fill_gradient_polygon(quad, stops, ((x0, y0), (x1, y1)), scaled)


def constant(value: float):
    """An `alpha_fn` that ignores its argument. Used for flat-alpha gradients."""
    return lambda _t: value


def shard_field(
    canvas: Canvas,
    palette,
    seed: int,
    cols: int = 9,
    rows: int = 7,
    jitter: float = 0.40,
    accent_edges: int = 12,
    alpha_scale: float = 1.0,
    specular: int = 5,
):
    """Triangulate the canvas into fine glass shards and light a few edges.

    A jittered lattice is split cell by cell along one of its two diagonals —
    the cheap, deterministic cousin of a Delaunay triangulation, and it gives
    the irregular facets the metaphor needs without pulling in a geometry
    library.

    Each facet is then filled with its *own* short gradient running along the
    light axis rather than one flat tone. That single change is what separates
    "faceted glass" from "triangles": neighbouring panes pick up a slightly
    different slice of the ramp, and panes near the light sit brighter than the
    ones falling away from it. `specular` panes facing the light get a faint
    bloom on top; `accent_edges` lattice edges refract into the spectrum, with
    the ones closer to the light winning the draw more often.
    """
    rng = Rng(seed)
    shade_far = hex_to_rgb(palette["shard_far"])
    shade_near = hex_to_rgb(palette["shard_near"])
    accents = [hex_to_rgb(c) for c in palette["accents"]]
    white = (255, 255, 255)
    core = hex_to_rgb(palette["core"])

    width, height = canvas.w, canvas.h
    origin = palette["light"]
    cx, cy = width * 0.5, height * 0.5
    ux, uy = origin[0] * width - cx, origin[1] * height - cy
    norm = math.hypot(ux, uy) or 1.0
    ux, uy = ux / norm, uy / norm
    reach = math.hypot(width, height) * 0.55
    axis = ((cx - ux * reach, cy - uy * reach), (cx + ux * reach, cy + uy * reach))
    adx, ady = axis[1][0] - axis[0][0], axis[1][1] - axis[0][1]
    denominator = adx * adx + ady * ady

    def along_axis(point):
        """0 at the far end of the light axis, 1 at the end beside the light."""
        t = ((point[0] - axis[0][0]) * adx + (point[1] - axis[0][1]) * ady) / denominator
        return 0.0 if t < 0 else (1.0 if t > 1 else t)

    step_x = 1.0 / cols
    step_y = 1.0 / rows
    lattice = {}
    for row in range(rows + 1):
        for col in range(cols + 1):
            x = col * step_x + rng.between(-jitter, jitter) * step_x
            y = row * step_y + rng.between(-jitter, jitter) * step_y
            lattice[(col, row)] = (x, y)

    triangles = []
    for row in range(rows):
        for col in range(cols):
            a = lattice[(col, row)]
            b = lattice[(col + 1, row)]
            c = lattice[(col + 1, row + 1)]
            d = lattice[(col, row + 1)]
            if ((col + row * 31) % 2) == 0:
                triangles.append((a, b, c))
                triangles.append((a, c, d))
            else:
                triangles.append((a, b, d))
                triangles.append((b, c, d))

    facets = []
    for tri in triangles:
        points = canvas.scale_polygon(tri)
        centroid = (
            (points[0][0] + points[1][0] + points[2][0]) / 3.0,
            (points[0][1] + points[1][1] + points[2][1]) / 3.0,
        )
        t = along_axis(centroid)
        # Mostly position, some chance: neighbouring panes stay related, but not
        # so related that the lattice becomes visible.
        base = mix(shade_far, shade_near, 0.55 * t + 0.45 * rng.next())
        alpha = palette["shard_alpha"] * alpha_scale * rng.between(0.72, 1.0)
        canvas.fill_gradient_polygon(
            points,
            [(0.0, mix(base, shade_far, 0.34)), (1.0, mix(base, shade_near, 0.34))],
            axis,
            alpha_fn=constant(alpha),
        )
        facets.append((t, points))

    for _t, points in sorted(facets, key=lambda facet: facet[0], reverse=True)[: max(0, specular)]:
        canvas.fill_polygon(points, mix(core, white, 0.45), palette["glow"] * 0.22)

    placed, attempts = 0, 0
    while placed < accent_edges and attempts < accent_edges * 10:
        attempts += 1
        tri = triangles[int(rng.next() * len(triangles)) % len(triangles)]
        edge = int(rng.next() * 3) % 3
        p0, p1 = tri[edge], tri[(edge + 1) % 3]
        midpoint = ((p0[0] + p1[0]) * 0.5 * width, (p0[1] + p1[1]) * 0.5 * height)
        t = along_axis(midpoint)
        if rng.next() > 0.18 + 0.82 * t:
            continue
        placed += 1
        colour = accents[int(rng.next() * len(accents)) % len(accents)]
        width_edge = rng.between(0.0011, 0.0032)
        peak = rng.between(0.40, 1.0) * (0.45 + 0.55 * t)
        canvas.stroke_unit_line(p0, p1, width_edge, colour, palette["edge_alpha"] * peak * 0.32)
        gradient_stroke(
            canvas,
            p0,
            p1,
            width_edge * 0.55,
            [(0.0, colour), (1.0, mix(colour, white, 0.30))],
            alpha_fn=lambda t: (1.0 - t) ** 1.6,
            alpha=palette["edge_alpha"] * peak,
        )

    return canvas


def soft_beam(canvas: Canvas, p0, p1, width: float, colour, peak: float):
    """A wide shaft of light: brightest in the middle, gone at both ends.

    The shaft is three nested quads rather than one. A single quad has two hard
    parallel sides and reads as a painted band; nesting a narrower and brighter
    quad inside each wider one fades the cross-section the way a beam of light
    does, and does it without the seams a segmented stroke would leave. The
    `share` values sum to roughly 1.1 so the core ends up as bright as the old
    single quad was, now that the edges are no longer at full strength.
    """
    inner = mix(colour, (255, 255, 255), 0.12)
    for scale, share in ((1.0, 0.30), (0.62, 0.36), (0.30, 0.44)):
        gradient_stroke(
            canvas,
            p0,
            p1,
            width * scale,
            [(0.0, colour), (0.5, inner), (1.0, colour)],
            alpha_fn=lambda t: math.sin(math.pi * t) ** 1.2,
            alpha=peak * share,
        )
    return canvas


def _rng_width(index: int) -> float:
    return (0.0012, 0.0016, 0.0014, 0.0011)[index % 4]


def glass_blur(canvas: Canvas, strength: int = 1) -> Canvas:
    """Blur radius scaled to the canvas, so a small render still looks like glass.

    A fixed radius would mean a different artwork at every resolution; scaling
    it keeps the preview and the shipped wallpaper the same picture.
    """
    radius = max(1, round(canvas.h / 540.0 * strength))
    return effects.box_blur(canvas, radius, 1)


def wallpaper_obsidian(palette, width: int, height: int) -> Canvas:
    """`0-obsidian-glass`: the whole sheet, lit from the upper right."""
    background = hex_to_rgb(palette["background"])
    surface = hex_to_rgb(palette["surface"])
    corner = hex_to_rgb(palette["corner"])
    core = hex_to_rgb(palette["core"])
    origin = palette["light"]

    canvas = Canvas(width, height)
    canvas.linear_gradient(
        (0, 0),
        (width, height),
        [(0.0, surface), (0.45, background), (1.0, corner)],
    )
    shard_field(canvas, palette, seed=20260930, cols=9, rows=7, jitter=0.42, accent_edges=14)
    canvas.radial_glow(
        (width * origin[0], height * origin[1]),
        max(width, height) * 0.55,
        mix(core, hex_to_rgb(palette["accents"][1]), 0.45),
        palette["glow"] * 0.75,
        3.0,
    )
    glass_blur(canvas, 1.4)
    effects.vignette(canvas, palette["vignette"])
    effects.add_noise(canvas, palette["noise"], 20260930)
    return canvas


def wallpaper_refraction(palette, width: int, height: int) -> Canvas:
    """`1-refraction`: one beam enters the glass and leaves as its spectrum."""
    background = hex_to_rgb(palette["background"])
    surface = hex_to_rgb(palette["surface"])
    corner = hex_to_rgb(palette["corner"])
    accent_colours = [hex_to_rgb(c) for c in palette["accents"]]
    white = (255, 255, 255)
    entry = (0.60, 0.80)

    canvas = Canvas(width, height)
    canvas.linear_gradient(
        (0, height),
        (width, 0),
        [(0.0, surface), (0.5, background), (1.0, corner)],
    )
    shard_field(
        canvas, palette, seed=77345, cols=8, rows=6, jitter=0.44, accent_edges=5, alpha_scale=0.78
    )

    # The beam arrives from off-canvas, so it reads as something entering the
    # frame rather than a shape painted on top of it.
    soft_beam(
        canvas,
        (-0.04, 0.02),
        entry,
        0.30,
        mix(accent_colours[1], white, 0.42),
        palette["glow"] * 1.05,
    )
    # Where it lands, the glass lights up.
    canvas.radial_glow(
        (entry[0] * width, entry[1] * height),
        max(width, height) * 0.24,
        mix(accent_colours[0], white, 0.30),
        palette["glow"] * 0.85,
        3.2,
    )

    # The split: hairlines leaving the entry point at different angles, each
    # fading out as it travels.
    fan = ((0.86, 0.66), (0.97, 0.46), (0.95, 0.22), (0.84, 0.02))
    for index, colour in enumerate(accent_colours[:4]):
        gradient_stroke(
            canvas,
            entry,
            fan[index],
            _rng_width(index) * 1.5,
            [(0.0, mix(colour, white, 0.40)), (1.0, colour)],
            alpha_fn=lambda t: (1.0 - t) ** 1.7,
            alpha=min(0.90, palette["edge_alpha"] * 1.6),
        )

    glass_blur(canvas, 1.5)
    effects.vignette(canvas, palette["vignette"] * 0.9)
    effects.add_noise(canvas, palette["noise"], 77345)
    return canvas


def wallpaper_quiet(palette, width: int, height: int) -> Canvas:
    """`2-quiet-glass`: almost nothing. One pane, two hairlines, no clutter.

    The pane sits under the light, so the corner nearest the source is the
    brightest thing on the canvas and the only prismatic detail is the edge it
    turns on.
    """
    background = hex_to_rgb(palette["background"])
    surface = hex_to_rgb(palette["surface"])
    corner = hex_to_rgb(palette["corner"])
    accents = [hex_to_rgb(c) for c in palette["accents"]]
    origin = palette["light"]

    canvas = Canvas(width, height)
    canvas.linear_gradient(
        (width, 0),
        (0, height),
        [(0.0, mix(surface, background, 0.35)), (0.6, background), (1.0, corner)],
    )

    canvas.fill_unit_gradient_polygon(
        [(0.44, -0.04), (1.05, -0.04), (1.05, 0.62)],
        [(0.0, mix(surface, background, 0.30)), (1.0, mix(surface, accents[0], 0.10))],
        ((1.05, 0.62), origin),
        alpha_fn=lambda t: 0.30 + 0.45 * t,
    )
    gradient_stroke(
        canvas,
        (0.44, -0.04),
        (1.05, 0.62),
        0.0024,
        [(0.0, accents[2]), (0.45, accents[1]), (1.0, accents[0])],
        alpha_fn=lambda t: math.sin(math.pi * t) ** 1.3,
        alpha=min(0.85, palette["edge_alpha"] * 1.35),
    )
    gradient_stroke(
        canvas,
        (0.50, 0.02),
        (0.86, 0.36),
        0.0012,
        [(0.0, accents[4]), (1.0, accents[3])],
        alpha_fn=lambda t: (1.0 - t) ** 1.8,
        alpha=palette["edge_alpha"] * 0.85,
    )

    glass_blur(canvas, 0.9)
    effects.vignette(canvas, palette["vignette"] * 1.1)
    effects.add_noise(canvas, palette["noise"], 4242)
    return canvas


DESIGNS = {
    "dark": (
        ("0-obsidian-glass", wallpaper_obsidian),
        ("1-refraction", wallpaper_refraction),
        ("2-quiet-glass", wallpaper_quiet),
    ),
    "light": (
        ("0-frosted-daylight", wallpaper_obsidian),
        ("1-prism-daylight", wallpaper_refraction),
        ("2-quiet-glass-light", wallpaper_quiet),
    ),
}

OUTPUT_DIRS = {
    "dark": REPO_ROOT / "backgrounds",
    "light": REPO_ROOT / "variants" / "light" / "backgrounds",
}


def parse_size(value: str):
    try:
        width, height = value.lower().split("x")
        return int(width), int(height)
    except Exception as error:  # noqa: BLE001
        raise SystemExit(f"--size wants WIDTHxHEIGHT, got {value!r}") from error


def write_image(canvas: Canvas, stem: Path, size, render_size, quality: int, fmt: str) -> Path:
    """Write one wallpaper, resampling/converting through `sips` when present."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    needs_resample = canvas.w != size[0] or canvas.h != size[1]
    sips = shutil.which("sips")

    if (needs_resample or fmt == "jpg") and not sips:
        if needs_resample:
            raise SystemExit(
                f"{stem.name}: need `sips` (macOS) to reach {size[0]}x{size[1]} from "
                f"{canvas.w}x{canvas.h}; pass --render-size {size[0]}x{size[1]} on Linux"
            )
        fmt = "png"

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "render.png"
        png.write_png(str(source), canvas.w, canvas.h, canvas.buf, canvas.channels)

        if fmt == "png" and not needs_resample:
            target = stem.with_suffix(".png")
            shutil.copy(source, target)
            return target

        target = stem.with_suffix(".jpg")
        command = [sips]
        if needs_resample:
            command += ["-z", str(size[1]), str(size[0])]
        command += [
            "-s",
            "format",
            "jpeg",
            "-s",
            "formatOptions",
            str(quality),
            str(source),
            "--out",
            str(target),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Prismatic Shards wallpapers.")
    parser.add_argument("--mode", choices=("dark", "light", "both"), default="both")
    parser.add_argument("--size", default="2560x1440", help="shipped resolution, e.g. 2560x1440")
    parser.add_argument("--render-size", default="1920x1080", help="internal render resolution")
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality when converting")
    parser.add_argument("--format", choices=("jpg", "png"), default="jpg")
    parser.add_argument("--only", default=None, help="substring filter on the design name")
    parser.add_argument("--dry-run", action="store_true", help="list what would be written")
    args = parser.parse_args(argv)

    size = parse_size(args.size)
    render = parse_size(args.render_size)
    modes = ("dark", "light") if args.mode == "both" else (args.mode,)

    written = []
    for mode in modes:
        palette = PALETTES[mode]
        for name, design in DESIGNS[mode]:
            if args.only and args.only not in name:
                continue
            target = OUTPUT_DIRS[mode] / name
            if args.dry_run:
                print(f"[dry-run] {mode:5s} {name} -> {target}.{args.format}")
                continue
            print(f"[{mode}] rendering {name} at {render[0]}x{render[1]} ...", flush=True)
            canvas = design(palette, render[0], render[1])
            path = write_image(canvas, target, size, render, args.quality, args.format)
            written.append(path)
            print(f"[{mode}] wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size // 1024} KB)")

    if written:
        total = sum(p.stat().st_size for p in written) // 1024
        print(f"\n{len(written)} wallpaper(s), {total} KB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
