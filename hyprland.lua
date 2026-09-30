-- Prismatic Shards — Liquid Glass tuning for Hyprland (dark)
--
-- Omarchy loads this file as `omarchy.current.theme.hyprland` (see
-- default/hypr/omarchy.lua in the Omarchy source), which is exactly where a
-- theme is allowed to shape the compositor. It is loaded *before* the user's
-- own `~/.config/hypr/looknfeel.lua`, so anything a user sets there still wins.
--
-- Two things to know:
--
--  1. Everything below runs inside `pcall`. If a future Hyprland renames a
--     key, the theme logs one line and the rest of the user's Hyprland config
--     still loads. A broken wallpaper is a bug; a broken session is not.
--
--  2. Omarchy's own default is flat on purpose — `rounding = 0`, no shadow,
--     no blur. Liquid Glass needs those three, so this file turns them on and
--     pairs them with alpha in shell.toml. If you want the flat default back,
--     set `decoration:rounding = 0`, `shadow:enabled = false` and
--     `blur:enabled = false` in ~/.config/hypr/looknfeel.lua: user config is
--     applied last, so it wins without touching this file.
--
-- Themes installed with `omarchy theme install` do not keep this file: Omarchy
-- drops `.lua` from themes cloned out of a git repo because a compositor
-- config can run code. Use ./install.sh (or copy the theme directory by hand)
-- to get the glass layer, and see docs/architecture.md.

local ok, err = pcall(function()
  -- Refracted-light borders. The generated hyprland.lua would derive these
  -- from colors.toml through the template; because this file replaces that
  -- output, it carries them literally.
  local active_border = {
    colors = { "rgba(4da3ffd9)", "rgba(8b7cffd9)", "rgba(f2a7d8b3)" },
    angle = 45,
  }
  local inactive_border = {
    colors = { "rgba(737b8833)", "rgba(171b22aa)" },
    angle = 45,
  }

  hl.config({
    general = {
      col = {
        active_border = active_border,
        inactive_border = inactive_border,
      },
      border_size = 2,
      -- The shell aligns its panels to general:gaps_out, so these keep
      -- floating windows and glass panels on the same rhythm.
      gaps_in = 5,
      gaps_out = 10,
    },

    group = {
      col = {
        border_active = active_border,
        border_inactive = inactive_border,
      },
    },

    decoration = {
      -- Style.cornerRadius in the Omarchy shell mirrors this value, so the
      -- bar, panels, notifications and the lock field all round together with
      -- the windows.
      rounding = 12,
      rounding_power = 2,

      -- Windows stay opaque; the glass is the UI layer. A depth cue comes from
      -- dim_inactive instead of from translucency, which keeps text crisp.
      active_opacity = 1.0,
      inactive_opacity = 0.97,
      dim_inactive = true,
      dim_strength = 0.06,

      shadow = {
        enabled = true,
        range = 22,
        render_power = 3,
        color = 0x66000000,
      },

      blur = {
        enabled = true,
        size = 6,
        passes = 3,
        new_optimizations = true,
        ignore_opacity = true,
        xray = false,
        noise = 0.015,
        contrast = 1.05,
        brightness = 1.0,
        popups = true,
        popup_opacity = 0.92,
        vibrancy = 0.1696,
        vibrancy_darkness = 0.0,
      },
    },

    animations = {
      enabled = true,
    },
  })

  -- Glass on the shell layers. Layer surfaces need an explicit rule; without
  -- one, the translucent alphas in shell.toml would show the wallpaper
  -- straight through instead of a blurred version of it.
  hl.layer_rule({
    name = "prismatic-blur-shell",
    match = {
      namespace = "^(omarchy-bar|omarchy-menu|omarchy-osd|omarchy-image-selector|omarchy-emojis|omarchy-clipboard|omarchy-keyboard-panel|omarchy-reminders|omarchy-network-qr)$",
    },
    blur = true,
  })
  hl.layer_rule({
    name = "prismatic-blur-dock",
    match = { namespace = "^prismatic-dock$" },
    blur = true,
  })
  -- The bar is chrome: it appears instantly rather than sliding in.
  hl.layer_rule({
    name = "prismatic-shell-crisp",
    match = { namespace = "^omarchy-bar$" },
    no_anim = true,
    animation = "none",
  })

  -- Motion. One shared bezier keeps window, layer and border movement in step,
  -- and a light spring on `windows` gives focus changes the settle that a
  -- macOS-style desktop has.
  hl.curve("prismaticGlass", { type = "bezier", points = { { 0.22, 1 }, { 0.36, 1 } } })
  hl.curve("prismaticSpring", { type = "spring", mass = 1, stiffness = 210, damping = 22 })

  hl.animation({ leaf = "windows", enabled = true, speed = 4.6, spring = "prismaticSpring" })
  hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.2, bezier = "prismaticGlass", style = "popin 92%" })
  hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.6, bezier = "linear", style = "popin 92%" })
  hl.animation({ leaf = "layers", enabled = true, speed = 4.0, bezier = "prismaticGlass" })
  hl.animation({ leaf = "border", enabled = true, speed = 5.0, bezier = "prismaticGlass" })
  hl.animation({ leaf = "fade", enabled = true, speed = 3.0, bezier = "quick" })

  -- Smooth cursor: prismatic theme at 32px, hardware-accelerated.
  hl.env("HYPRCURSOR_THEME", "Prismatic-Shards")
  hl.env("HYPRCURSOR_SIZE", "32")
  hl.env("XCURSOR_THEME", "Prismatic-Shards")
  hl.env("XCURSOR_SIZE", "32")
end)

if not ok then
  print("[prismatic-shards] Hyprland glass tuning skipped: " .. tostring(err))
end
