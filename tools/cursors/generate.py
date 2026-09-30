#!/usr/bin/env python3
"""Generate the Prismatic-Shards cursor theme for hyprcursor and xcursor.

Every cursor in `cursor/hyprcursor/Prismatic-Shards/` (dark) and
`cursor/xcursor/Prismatic-Shards/` (fallback) is produced by this script.
Nothing is downloaded and nothing is traced from a photograph: a sheet of glass
is triangulated into shards; almost all of it stays graphite; the light that hits
it splits into blue, cyan, violet, magenta and pink along a few edges only.

The metaphor is literal here, which is the point. A cursor is generated from a
fixed seed, and the same seed produces the same cursor, byte for byte.

Usage
-----
    python3 tools/cursors/generate.py --mode dark --size 32
    python3 tools/cursors/generate.py --mode light --size 32
    python3 tools/cursors/generate.py --mode both

Development tooling only: the installed theme ships finished images and never runs
Python.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geometry import (
    all_shapes,
    shape_crosshair,
    shape_default,
    shape_grab,
    shape_grabbing,
    shape_help,
    shape_not_allowed,
    shape_pointer,
    shape_progress,
    shape_resize,
    shape_text,
    shape_wait,
    shape_zoom,
)
from raster import PALETTES, Part, Stroke, render

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HYPRCURSOR_DIR = REPO_ROOT / "cursor" / "hyprcursor" / "Prismatic-Shards"
XCURSOR_DIR = REPO_ROOT / "cursor" / "xcursor" / "Prismatic-Shards"

# Cursor sizes supported by hyprcursor
SUPPORTED_SIZES = [24, 32, 48, 64, 128, 256]

# hyprcursor version required
hyprcursor_version = "0.1"

# Cursor metadata template
METADATA_TEMPLATE = {
    "name": "Prismatic-Shards",
    "version": "1.0.0",
    "comment": "Fractured light. Unified system.",
    "author": "Ali Akbar Hyder",
    "license": "Prismatic Shards Personal Use License",
    "repository": "https://github.com/aliakbarhyder/prismaticshards",
    "homepage": "https://github.com/aliakbarhyder/prismaticshards",
    "description": "Liquid Glass-inspired Omarchy theme with prismatic color system. Includes smooth, spring-like cursor movement with prismatic blue, violet and pink accents.",
}

def create_hyprcursor_theme_dir():
    """Create the hyprcursor theme directory structure."""
    theme_dir = HYPRCURSOR_DIR
    theme_dir.mkdir(parents=True, exist_ok=True)
    
    # Create required hyprcursor files
    (theme_dir / "index.json").write_text(json.dumps({
        "version": hyprcursor_version,
        "name": METADATA_TEMPLATE["name"],
        "comment": METADATA_TEMPLATE["comment"],
    }, indent=2))
    
    # Create file for each supported size
    for size in SUPPORTED_SIZES:
        (theme_dir / f"cursors{size}").mkdir(exist_ok=True)

def create_xcursor_theme_dir():
    """Create the xcursor theme directory structure."""
    theme_dir = XCURSOR_DIR
    theme_dir.mkdir(parents=True, exist_ok=True)
    
    # Create package.xml for xcursor
    package_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<icon-theme version="0.1">
  <name>{METADATA_TEMPLATE["name"]}</name>
  <comment>{METADATA_TEMPLATE["comment"]}</comment>
  <author>{METADATA_TEMPLATE["author"]}</author>
  <email>{METADATA_TEMPLATE["name"]}@{METADATA_TEMPLATE["author"].lower().replace(" ", "")}.com</email>
  <homepage>{METADATA_TEMPLATE["homepage"]}</homepage>
  <keywords>glass, prismatic, light, unified</keywords>
  <licenses>
    <license>{METADATA_TEMPLATE["license"]}</license>
  </licenses>
</icon-theme>
"""
    (theme_dir / "package.xml").write_text(package_xml)

def get_cursor_shapes():
    """Return all cursor shapes in the correct order."""
    return all_shapes()

def _palette_for(mode: str):
    key = "prismatic-shards-light" if mode == "light" else "prismatic-shards"
    return PALETTES[key]

def generate_hyprcursor_files(mode: str):
    """Generate hyprcursor cursor files for the specified mode."""
    theme_dir = HYPRCURSOR_DIR
    theme_dir.mkdir(parents=True, exist_ok=True)
    
    shapes = get_cursor_shapes()
    
    # Generate cursors for each size
    for size in SUPPORTED_SIZES:
        size_dir = theme_dir / f"{size}"
        size_dir.mkdir(exist_ok=True)
        
        for shape in shapes:
            cursor_name = shape.aliases[0]  # Use first alias as identifier
            try:
                pixels = render(shape.parts, shape.strokes, size,
                                _palette_for(mode), shadow=True)
                
                # Save cursor image
                image_file = size_dir / f"{cursor_name}.png"
                save_cursor_image(pixels, image_file, size, size)
                
                # Save cursor metadata
                metadata = {
                    "name": METADATA_TEMPLATE["name"],
                    "version": METADATA_TEMPLATE["version"],
                    "comment": METADATA_TEMPLATE["comment"],
                    "type": "png",
                    "hotspot_x": round(shape.hotspot[0] * size),
                    "hotspot_y": round(shape.hotspot[1] * size),
                    "shape": shape.name,
                }
                
                (size_dir / f"{cursor_name}.info.json").write_text(
                    json.dumps(metadata, indent=2)
                )
                
            except Exception as e:
                print(f"[ERROR] Failed to generate {cursor_name} cursor at {size}px: {e}")
                continue

def generate_xcursor_files(mode: str):
    """Generate xcursor cursor files for the specified mode."""
    theme_dir = XCURSOR_DIR
    theme_dir.mkdir(parents=True, exist_ok=True)
    
    shapes = get_cursor_shapes()
    
    # Generate cursors for standard sizes (24, 32, 48, 64)
    for size in [24, 32, 48, 64]:
        size_dir = theme_dir / f"{size}"
        size_dir.mkdir(exist_ok=True)
        
        for shape in shapes:
            cursor_name = shape.aliases[0]
            try:
                pixels = render(shape.parts, shape.strokes, size,
                                _palette_for(mode), shadow=True)
                
                # Save cursor image
                image_file = size_dir / f"{cursor_name}.png"
                save_cursor_image(pixels, image_file, size, size)
                
            except Exception as e:
                print(f"[ERROR] Failed to generate xcursor {cursor_name} at {size}px: {e}")
                continue

def save_cursor_image(pixels: bytes, path: Path, width: int, height: int):
    """Save cursor image to PNG file (stdlib only, no Pillow)."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from lib.png import write_png

    path.parent.mkdir(parents=True, exist_ok=True)
    write_png(str(path), width, height, bytes(pixels), channels=4)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the Prismatic-Shards cursor theme.")
    parser.add_argument("--mode", choices=("dark", "light", "both"), default="both", 
                       help="Cursor theme mode (affects colors and palette)")
    parser.add_argument("--size", type=int, default=32,
                       help="Base cursor size (other sizes derived)")
    parser.add_argument("--dry-run", action="store_true",
                       help="List what would be written without writing files")
    args = parser.parse_args(argv)
    
    modes = ("dark", "light") if args.mode == "both" else (args.mode,)
    
    print(f"[cursor] Generating Prismatic-Shards cursor theme...")
    print(f"[cursor] Mode: {args.mode}")
    print(f"[cursor] Base size: {args.size}px")
    
    # Create directory structure
    if args.dry_run:
        print(f"[dry-run] Would create hyprcursor theme at: {HYPRCURSOR_DIR}")
        print(f"[dry-run] Would create xcursor theme at: {XCURSOR_DIR}")
    else:
        create_hyprcursor_theme_dir()
        create_xcursor_theme_dir()
    
    # Generate cursors for each mode
    for mode in modes:
        print(f"[{mode}] Generating cursors...")
        
        if not args.dry_run:
            generate_hyprcursor_files(mode)
            generate_xcursor_files(mode)
            
            # Generate metadata file
            theme_dir = HYPRCURSOR_DIR
            metadata = METADATA_TEMPLATE.copy()
            metadata["mode"] = mode
            metadata["sizes"] = SUPPORTED_SIZES
            import datetime as _dt
            metadata["generated_at"] = _dt.datetime.now(
                _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            (theme_dir / "metadata.json").write_text(
                json.dumps(metadata, indent=2)
            )
        
        print(f"[{mode}] Done.")
    
    if not args.dry_run:
        total_size = sum(f.stat().st_size for f in HYPRCURSOR_DIR.rglob("*") if f.is_file()) // 1024
        print(f"[cursor] Generated cursor theme: {len(SUPPORTED_SIZES) * len(get_cursor_shapes())} cursors, {total_size} KB total")

if __name__ == "__main__":
    raise SystemExit(main())
