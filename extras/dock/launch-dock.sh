#!/bin/bash
# Launch the Prismatic Shards floating dock (liquid-glass, macOS-style).
set -euo pipefail
CFG="$HOME/.config/prismatic-shards/dock.conf"
REPO_CFG="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/extras/dock/dock.conf"
[[ -f "$CFG" ]] || { mkdir -p "$(dirname "$CFG")"; cp -f "$REPO_CFG" "$CFG"; }
if ! command -v nwg-dock-hyprland >/dev/null 2>&1; then
  echo "nwg-dock-hyprland not installed. Install with: yay -S nwg-dock-hyprland" >&2
  exit 1
fi
export XCURSOR_THEME="Prismatic-Shards"
export HYPRCURSOR_THEME="Prismatic-Shards"
export HYPRCURSOR_SIZE=32
exec nwg-dock-hyprland -c "$CFG" -n "prismatic-dock"
