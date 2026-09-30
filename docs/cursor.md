# Prismatic Shards Custom Cursor Theme

## Overview

Prismatic Shards includes a custom cursor theme inspired by Magic UI's SmoothCursor design. The cursor theme features:

- Smooth, spring-like movement with subtle smoothing
- Responsive motion with tiny rotation response
- Polished hover interactions
- Native Wayland-compatible implementation
- Prismatic color accents that match the theme

## Cursor Architecture

The cursor theme uses a multi-layered rendering approach:

1. **Outlines** — First layer, defining the cursor silhouette
2. **Body** — Second layer, filling the cursor shape
3. **Danger** — Third layer, for warning/error states
4. **Accent** — Fourth layer, prismatic highlights and active states
5. **Refract** — Fifth layer, light refraction effects

### Rendering Pipeline

1. **Path Definition** — Cursors are defined in unit space (0-1 coordinate system)
2. **Flattening** — Convert Bézier curves to polylines with bounded chord error
3. **Rasterization** — Compute per-pixel coverage using supersampling (4x4 grid)
4. **Stroke Outline** — Create stroke outlines using filled strokes
5. **Composition** — Composite layers with alpha blending