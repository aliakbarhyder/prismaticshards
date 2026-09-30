# Prismatic Shards Theme Switching

## Overview

Prismatic Shards implements smooth theme switching between dark and light modes. The switching system is inspired by Magic UI's AnimatedThemeToggler but implemented natively for Omarchy/Hyprland.

## Switching Mechanism

### Overview

The theme switching system uses a circular/radial reveal approach that affects:

- Menu bar
- Dock
- Launcher
- Control Center
- Terminal
- GTK applications
- Qt applications
- Notifications
- OSD
- Lock screen
- Wallpaper
- Cursor accents

### Switching Process

1. **Trigger** — User activates theme switcher (typically via control center or system menu)
2. **Animation** — Circular reveal animation from toggle position
3. **Theme Change** — Hyprland configuration updated, shell tokens regenerated
4. **Render Update** — All affected UI components updated
5. **Cursor Update** — Cursor theme palette switched
6. **Wallpaper Update** — Background wallpaper changed if needed

## Implementation Details

### Animation System

The theme uses custom Bezier curves for smooth transitions:

```lua
-- Glass-like transitions
hl.curve("prismaticGlass", { type = "bezier", points = { { 0.22, 1 }, { 0.36, 1 } } })

-- Spring-based animations for responsive feel
hl.curve("prismaticSpring", { type = "spring", mass = 1, stiffness = 210, damping = 22 })
```

### Duration and Timing

- **Animation Duration** — 300-600ms for smooth transitions
- **Reveal Type** — Circular/radial reveal from toggle position
- **Easing** — Custom Bezier curves for macOS-like feel
- **Trigger Points** — Multiple entry points for theme switching