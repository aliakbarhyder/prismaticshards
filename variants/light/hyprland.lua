-- Prismatic Shards — Liquid Glass tuning for Hyprland (light)
--
-- The companion of the dark theme's hyprland.lua. Same contract, same
-- `pcall` safety net, same layer rules; daylight values. See that file and
-- docs/architecture.md for the reasoning.

local ok, err = pcall(function()
  local active_border = {
    colors = { "rgba(1677ffcc)", "rgba(705febbb)", "rgba(d889baa6)" },
    angle = 45,
  }
  local inactive_border = {
    colors = { "rgba(89919d4d)", "rgba(e9ecf1e6)" },
    angle = 45,
  }

  hl.config({
    general = {
      col = {
        active_border = active_border,
        inactive_border = inactive_border,
      },
      border_size = 2,
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
      rounding = 12,
      rounding_power = 2,
      active_opacity = 1.0,
      inactive_opacity = 0.97,
      dim_inactive = true,
      dim_strength = 0.04,

      shadow = {
        enabled = true,
        range = 20,
        render_power = 2,
        -- Daylight shadows are softer and cooler than the dark theme's.
        color = 0x33000000,
      },

      blur = {
        enabled = true,
        size = 7,
        passes = 3,
        new_optimizations = true,
        ignore_opacity = true,
        xray = false,
        noise = 0.008,
        contrast = 1.02,
        brightness = 1.04,
        popups = true,
        popup_opacity = 0.94,
        vibrancy = 0.12,
        vibrancy_darkness = 0.0,
      },
    },

    animations = {
      enabled = true,
    },
  })

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
  hl.layer_rule({
    name = "prismatic-shell-crisp",
    match = { namespace = "^omarchy-bar$" },
    no_anim = true,
    animation = "none",
  })

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
