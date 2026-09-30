#!/usr/bin/env python3
"""Terminal preview helper (developer tool, not part of the build).

Renders a cursor at a given size and prints it as ASCII art so shapes can be
sanity-checked on a machine without an image viewer::

    python3 tools/cursors/ascii_preview.py --size 32 default pointer
    python3 tools/cursors/ascii_preview.py --all --size 24

Legend:  ``#`` body   ``.`` outline   ``B`` accent   ``R`` danger
         ``V`` refraction   ``,`` drop shadow   (space) transparent
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geometry      # noqa: E402
import raster        # noqa: E402


def classify(rgba: bytes, index: int) -> str:
    r, g, b, a = rgba[index], rgba[index + 1], rgba[index + 2], rgba[index + 3]
    if a < 32:
        return " "
    if b > 150 and r < 130 and g < 170:
        return "B"                      # accent blue
    if r > 150 and b < 140 and g < 130:
        return "R" if a > 120 else ","  # danger red
    if r > 150 and b > 150 and g < 150:
        return "V"                      # violet refraction
    if a < 200 and r < 60 and g < 60:
        return ","                      # soft shadow
    if r > 150 and g > 150 and b > 150:
        return "#"                      # body
    return "."                          # outline / dark edge


def show(rgba: bytes, size: int, label: str) -> None:
    print(f"--- {label} ({size}x{size}) ---")
    for y in range(size):
        row = "".join(classify(rgba, (y * size + x) * 4) for x in range(size))
        print("|" + row + "|")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="shape names (default: all)")
    parser.add_argument("--size", type=int, default=32)
    parser.add_argument("--light", action="store_true",
                        help="use the light (preview) palette")
    args = parser.parse_args(argv)

    palette = raster.PALETTE_LIGHT if args.light else raster.PALETTE_DARK
    shapes = geometry.all_shapes()
    if args.names:
        wanted = set(args.names)
        shapes = [s for s in shapes if s.name in wanted or wanted & set(s.aliases)]
        if not shapes:
            parser.error("no shape matched " + ", ".join(sorted(wanted)))
    for shape in shapes:
        rgba = raster.render(shape.parts, shape.strokes, args.size, palette)
        show(rgba, args.size, shape.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
