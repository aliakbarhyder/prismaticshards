# Prismatic Shards Omarchy Theme - Code Documentation

## Overview

The Prismatic Shards Omarchy theme is a complete Liquid Glass aesthetic theme with prismatic color system implementation for Omarchy Linux systems. This theme features fractured light refraction effects, glass translucency, and a unified prismatic color palette.

## File Structure

```
/prismaticshards/
├── README.md                    # Main documentation
├── LICENSE                      # Restrictive usage license
├── .gitignore                   # Git ignore rules
├── colors.toml                  # Main theme colors (dark/light)
├── shell.toml                   # Shell configuration
├── shell.lock.toml              # Lock screen overrides
├── hyprland.lua                 # Hyprland integration
├── icons.theme                  # Icon theme reference
├── backgrounds/                 # Dark theme wallpapers (512KB)
├── backgrounds_light/            # Light theme wallpapers (512KB)
├── variants/
│   ├── light/
│   │   ├── colors.toml          # Light theme colors
│   │   ├── shell.toml           # Light shell config
│   │   └── hyprland.lua         # Light Hyprland config
└── (additional directories)
```

## Core Theme Files Documentation

### 1. README.md
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/README.md`

**Purpose**: Main documentation for the Prismatic Shards Omarchy theme

**Key Content**:
- Overview of the Liquid Glass aesthetic theme
- Feature list including:
  - Liquid Glass Aesthetic: Translucency, blur, thin borders, shadows, layered surfaces
  - Dual Themes: Dark Obsidian and Light Frosted Glass modes
  - macOS-inspired Layout with floating dock and top menu bar
  - Prismatic Color System with 5 accent colors (blue, cyan, violet, magenta, pink)
  - Hyprland Integration with custom window borders and glass effects
  - Custom Cursor Theme with SmoothCursor-inspired behavior
  - Control Center with Wi-Fi, Bluetooth, volume, brightness controls
  - Theme Switching with smooth radial/circular reveal effects

**Design Philosophy**:
- Visual metaphor of dark glass surface fractured into geometric shards
- When light hits edges, it splits into prismatic colors
- Dark mode: Obsidian glass with blue/cyan/violet/pink highlights
- Light mode: Frosted glass with subtle daylight refraction
- Minimal geometric shards and subtle refractions

### 2. LICENSE
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/LICENSE`

**Purpose**: Restrictive usage license for personal use only

**Key Restrictions**:
- **Editing Prohibition**: Cannot modify, edit, alter, or create derivative works
- **Commercial Use Prohibition**: Cannot resell, distribute for profit, or commercially exploit
- **Distribution Limitations**: Original unmodified files only for backup purposes
- **Attribution Required**: Must retain all copyright notices and credit "Prismatic Shards"
- **No Warranties**: Provided "AS IS" without warranties

**License Terms**:
- Copyright (c) 2026 Ali Akbar Hyder and Prismatic Shards contributors
- Permission to download and access for personal use, research, and evaluation
- All rights reserved - no editing, modification, or commercial use allowed
- Legal action for violations

### 3. .gitignore
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/.gitignore`

**Purpose**: Git ignore rules for development environment

**Ignored Items**:
- macOS system files: `.DS_Store`, `._*`, `.AppleDouble`, `.LSOverride`
- Editor/IDE files: `.vscode/`, `.idea/`, `*.swp`, `*.swo`, `*~`
- Python artifacts: `__pycache__/`, `*.py[cod]`, `.venv/`, `.mypy_cache/`
- Node.js tooling: `node_modules/`, `npm-debug.log*`, `yarn-error.log*`
- Build artifacts: `build/`, `dist/`, `*.tmp`, `*.log`, `/tmp/`, `.cache/`
- Secrets: `.env`, `*.pem`, `*.key`, `*.p12`, `id_rsa*`, `known_hosts`, `secrets/`

### 4. colors.toml
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/colors.toml`

**Purpose**: Omarchy theme contract defining color palette and tokens

**Structure**:
- `mode = "dark"` - Specifies theme mode
- Semantic color groups following Omarchy conventions:
  - `accent`, `selection`, `muted` - Interactive elements
  - `background`, `foreground`, `surface`, `elevated` - Core layout
  - Named hues: `red`, `yellow`, `orange`, `green`, `cyan`, `blue`, `magenta`, `brown`

**Prismatic Extension Tokens**:
- `surface = "#11151A"` - Secondary surfaces
- `elevated = "#171B22"` - Elevated elements
- `violet = "#8B7CFF"` - Prismatic violet accent
- `pink = "#F2A7D8"` - Prismatic pink accent

**Dark Theme Colors**:
- **Background**: `#08090B` (obsidian)
- **Foreground**: `#F2F4F8` (near white)
- **Accent**: `#4DA3FF` (blue)
- **Prismatic Colors**: Blue `#4DA3FF`, Cyan `#63D7FF`, Violet `#8B7CFF`, Pink `#F2A7D8`

**Hyprland Active Border**:
```toml
hyprland_active_border = "rgba(4da3ffd9) rgba(8b7cffd9) rgba(f2a7d8b3) 45deg"
```
Creates gradient borders simulating light refraction through glass edges.

### 5. shell.toml
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/shell.toml`

**Purpose**: Omarchy shell surfaces configuration

**Liquid Glass Rules Applied**:
- Surfaces maintain alpha between 0.65-1.0 for readability
- Blur comes from Hyprland layer rules (not alpha)
- Borders are 1px and mostly transparent
- Accent colors reserved for active/selected states

**Configuration Sections**:

#### [bar] - Top menu bar
- `background = "#08090B"` - Obsidian background
- `background-alpha = 0.68` - Translucent glass
- `text = "#F2F4F8"` - Light text for contrast
- `active = "#C77DFF"` - Active/highlight color

#### [hyprland] - Window management integration
- `active-border = "rgba(4da3ffd9) rgba(8b7cffd9) rgba(f2a7d8b3) 45deg"` - Prismatic border gradient
- `active-border-foreground = "rgba(f2f4f8e6) rgba(63d7ffe6) 45deg"` - Border text color

#### [controls] - Interactive elements styling
- Normal controls: Subtle transparency (`normal-fill-alpha = 0.05`)
- Hover states: Enhanced visibility (`hover-cursor-fill-alpha = 0.10`)
- Focus states: Prismatic accent (`focus-border = "#63D7FF"`)
- Selected states: Blue accent (`selected-border = "#4DA3FF"`)

#### [popups] and [tooltip] - UI popups
- High transparency (`background-alpha = 0.86`, `0.94` respectively)
- Glass-like borders referencing Hyprland active borders
- Clean, readable text on transparent backgrounds

#### [launcher] and [menu] - Application launchers
- Dark backgrounds with glass effects
- Selected items use prismatic blue (`selected-background = "#4DA3FF"`)

### 6. shell.lock.toml
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/shell.lock.toml`

**Purpose**: Lock screen overrides for specialized appearance

**Key Differences from Default shell.toml**:
- `background-alpha = 0.70` - Slightly less transparent than default (0.72)
- `border-alpha = 0.90` - Nearly opaque borders for security
- Custom border: `"rgba(737b88b3) rgba(171b22aa) 45deg"` - Subtle gradient
- Selection uses prismatic blue (`selection = "#4DA3FF"`)

### 7. hyprland.lua
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/hyprland.lua`

**Purpose**: Hyprland compositor integration for Liquid Glass effects

**Core Features**:
- **Refracted-light borders**: Gradient borders simulating light through glass
- **Liquid Glass tuning**: Rounding, shadows, blur for macOS-like aesthetics
- **Layer rules**: Special blur effects for shell surfaces
- **Custom animations**: Smooth window and layer transitions

**Configuration Highlights**:

#### Window Borders
```lua
local active_border = {
  colors = { "rgba(4da3ffd9)", "rgba(8b7cffd9)", "rgba(f2a7d8b3)" },
  angle = 45,
}
```
Creates the signature prismatic gradient borders.

#### Glass Effects
- `rounding = 12` with `rounding_power = 2` - Consistent rounded corners
- `shadow = { enabled = true, range = 22, render_power = 3, color = 0x66000000 }` - Subtle shadows
- `blur = { enabled = true, size = 6, passes = 3, ... }` - Multi-pass blur for glass effect

#### Layer Rules
- `prismatic-blur-shell`: Blurs shell surfaces (bar, menu, notifications)
- `prismatic-blur-dock`: Blurs the prismatic dock
- `prismatic-shell-crisp`: Makes bar layer non-animated for instant appearance

#### Animations
- `prismaticSpring`: Spring-based animation for smooth window movements
- `prismaticGlass`: Bezier curve for glass-like transitions
- Custom speeds for windows, layers, borders, and fades

### 8. icons.theme
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/icons.theme`

**Content**: `Yaru-blue`
**Purpose**: Icon theme reference for compatibility

### 9. variants/light/colors.toml
**Location**: `/Volumes/megastorage/AAH/Theme/prismaticshards/variants/light/colors.toml`

**Purpose**: Light theme color palette

**Key Differences**:
- `mode = "light"` - Specifies light theme mode
- Lighter backgrounds: `#F3F5F8` (frosted), `#FFFFFF` (pure)
- Darker foregrounds: `#16181C` for text contrast
- Adjusted prismatic colors for daylight:
  - `violet = "#705FE8"` (lighter violet)
  - `pink = "#D889BA"` (softer pink)