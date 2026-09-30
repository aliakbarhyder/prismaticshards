# Prismatic-Shards XCursor Theme

## Overview

Prismatic-Shards is the XCursor fallback implementation for systems without native Hyprcursor support.

## Features

- All Prismatic-Shards cursor states available
- X11-compatible format
- Automatic theme adaptation
- Lightweight implementation

## Installation

```bash
sudo cp -r cursor/xcursor/Prismatic-Shards ~/.icons/
```

Set in your desktop environment:
```bash
gsettings set org.gnome.desktop.interface cursor-theme "Prismatic-Shards"
gsettings set org.gnome.desktop.interface cursor-size 32
```

## Files Included

- `32/` — Cursor files at 32px size
- `package.xml` — Theme metadata
- `README.md` — This documentation

## Compatibility

- X11 desktop environments
- GTK applications
- Qt applications
- Fallback for systems without hyprcursor

## References

- XCursor specification
- GTK cursor theming
- Qt cursor integration
