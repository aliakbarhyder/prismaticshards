# Prismatic Shards

**Fractured light. Unified system.**

> Imagine what Omarchy could look like with Apple-level attention to UI polish, but retaining Linux's identity and flexibility.

## Overview

Prismatic Shards is a Liquid Glass-inspired Omarchy theme that brings modern macOS aesthetics to the Linux desktop while maintaining its unique identity. The theme features a dark and light mode system with prismatic color accents that represent light refracting through glass.

## Features

- **Liquid Glass Aesthetic**: Translucency, blur, thin borders, shadows, and layered surfaces
- **Dual Themes**: Dark Obsidian and Light Frosted Glass modes
- **macOS-inspired Layout**: Thin top menu bar, floating dock, glass popovers
- **Prismatic Color System**: Blue, cyan, violet, magenta, and pink accents representing light refraction
- **Hyprland Integration**: Custom window borders and glass effects
- **Custom Cursor Theme**: Smooth, prismatic design inspired by Magic UI
- **Control Center**: Original glass panel with Wi-Fi, Bluetooth, volume, brightness controls
- **Theme Switching**: Smooth transitions between light and dark modes
- **Documentation**: Complete architecture and implementation guides

## Design Philosophy

The visual metaphor is a dark glass surface fractured into extremely fine geometric shards. When light hits the surface, most of it remains dark, but at certain edges, it splits into:

- Blue
- Cyan
- Violet
- Magenta
- Pink

These are the prismatic accents that appear subtly in focused windows, dock hover states, active controls, selected launcher items, and during theme transitions.

## Color System

Based on the Omarchy `colors.toml` architecture, providing semantic color names like:

- `background`, `foreground`
- `accent`, `muted`, `selection`
- `surface`, `elevated`, `violet`, `pink`
- And more semantic color tokens for UI components

## Light/Dark Modes

- **Dark Theme**: Obsidian glass with blue/cyan/violet/pink prismatic highlights
- **Light Theme**: Frosted glass with subtle daylight refraction
- **Theme Transitions**: Radial/circular reveal effects from toggle position

## Technical Architecture

- **Omarchy Compatibility**: Uses actual Omarchy theme format (`colors.toml`, `shell.toml`, `hyprland.lua`)
- **Wayland/Hyprland**: Native integration with the Hyprland compositor
- **Performance**: Minimal runtime requirements, primarily configuration and assets
- **Licensing**: Original assets with appropriate open-source licensing

## Installation

1. **For Omarchy Users**:
   ```bash
   # Clone this repository
   git clone https://github.com/aliakbarhyder/prismaticshards.git
   # Install using Omarchy's theme system
   omarchy theme install prismatic-shards
   ```

2. **Manual Installation**:
   ```bash
   # Copy theme to your Omarchy themes directory
   cp -r prismatic-shards ~/.config/omarchy/themes/
   # Reload Omarchy
   ```

## Uninstallation

```bash
omarchy theme uninstall prismatic-shards
# or manually remove the theme directory
rm -rf ~/.config/omarchy/themes/prismatic-shards
```

## Cursor Theme

The custom cursor theme `Prismatic-Shards` uses hyprcursor with SmoothCursor-inspired behavior:

- Spring-like movement with subtle smoothing
- Responsive motion with tiny rotation response
- Polished hover interactions
- Native Wayland-compatible implementation

## Dock and Menu Bar

- **macOS-inspired floating dock** with glass aesthetics
- **Top menu bar** with Prismatic Shards launcher, clock, system controls
- **Functional controls**: Wi-Fi, Bluetooth, volume, battery, notifications
- **Hover animations** and active state indicators

## Control Center

An original glass-style system panel with modules:

- Wi-Fi
- Bluetooth
- Volume
- Brightness
- Battery
- Dark/Light mode toggle
- Night Light
- Do Not Disturb
- Media controls

## Documentation

- `docs/architecture.md` - Theme architecture and integration details
- `docs/cursor.md` - Custom cursor implementation
- `docs/theme-switching.md` - Light/dark theme system

## Preview

- Dark mode screenshots showing menu bar, dock, terminal, launcher
- Light mode equivalents
- Prismatic highlight effects in action
- Glass control center and cursor

## Compatibility

- **Omarchy**: ✅ Native theme format support
- **Hyprland**: ✅ Custom window management and effects
- **Wayland**: ✅ Native Wayland integration
- **Linux**: ✅ Requires Linux environment

## Known Limitations

- Some macOS-inspired features may not have direct Omarchy equivalents
- Advanced cursor animations require hyprcursor support
- Control center functionality limited to available system APIs

## Development

This repository is a complete Omarchy theme following the project's conventions:

- Uses `colors.toml` for color management
- Provides `shell.toml` for UI theming
- Includes `hyprland.lua` for compositor integration
- Original assets and configurations (no macOS copyright material)

## License

This theme is provided under an open-source license appropriate for Omarchy themes. See `LICENSE` for details.

All original assets created for this theme are released under the same license. External dependencies (like Yaru icons) maintain their own licenses.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow the existing code style
4. Add documentation for new features
5. Ensure all theme files maintain Omarchy compatibility

## Credits

Inspired by:
- Modern macOS Liquid Glass design
- Magic UI SmoothCursor and AnimatedThemeToggler (design references only)
- Omarchy theme architecture and conventions
- Hyprland and Wayland ecosystem

## Final Status

✅ **Repository**: Complete and ready
✅ **Theme Files**: All Omarchy-compatible theme files present
✅ **Documentation**: Comprehensive guides and architecture docs
✅ **Installation**: Clean install/uninstall scripts
✅ **GitHub**: Published to aliakbarhyder/prismaticshards

The theme is production-ready for Omarchy Linux users seeking a premium, polished desktop experience with Liquid Glass aesthetics.
