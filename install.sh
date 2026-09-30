#!/bin/bash
# Prismatic Shards Omarchy Theme Installer
# Installs dark + light themes, wallpapers, cursors, dock + toggle.
# Author: Ali Akbar Hyder
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DARK="prismatic-shards"; THEME_LIGHT="prismatic-shards-light"
COPY_ONLY=false; [[ "${1:-}" == "--copy-only" ]] && COPY_ONLY=true
check_files() {
  local missing=0
  for f in colors.toml shell.toml shell.lock.toml hyprland.lua icons.theme keyboard.rgb preview.png; do
    [[ -f "$SCRIPT_DIR/$f" ]] || { log_error "missing $f"; missing=1; }
  done
  for f in variants/light/colors.toml variants/light/shell.toml variants/light/shell.lock.toml variants/light/hyprland.lua variants/light/icons.theme variants/light/keyboard.rgb variants/light/preview.png; do
    [[ -f "$SCRIPT_DIR/$f" ]] || { log_error "missing $f"; missing=1; }
  done
  [[ -d "$SCRIPT_DIR/backgrounds" ]] || { log_error "missing backgrounds/"; missing=1; }
  [[ -d "$SCRIPT_DIR/variants/light/backgrounds" ]] || { log_error "missing variants/light/backgrounds/"; missing=1; }
  [[ -d "$SCRIPT_DIR/cursor/hyprcursor/Prismatic-Shards" ]] || { log_error "missing cursor theme"; missing=1; }
  [[ -f "$SCRIPT_DIR/scripts/prismatic-shards-theme-toggle" ]] || { log_error "missing theme toggle"; missing=1; }
  [[ -f "$SCRIPT_DIR/extras/dock/dock.conf" ]] || { log_error "missing dock.conf"; missing=1; }
  return $missing
}
install_theme_dir() {
  local src="$1" dest="$2" label="$3"
  log_info "Installing $label -> $dest"
  mkdir -p "$dest/backgrounds"
  cp -f "$src/colors.toml" "$dest/colors.toml"
  cp -f "$src/shell.toml" "$dest/shell.toml"
  cp -f "$src/shell.lock.toml" "$dest/shell.lock.toml" 2>/dev/null || true
  cp -f "$src/icons.theme" "$dest/icons.theme"
  cp -f "$src/keyboard.rgb" "$dest/keyboard.rgb"
  cp -f "$src/hyprland.lua" "$dest/hyprland.lua" 2>/dev/null || true
  cp -f "$src/backgrounds/"* "$dest/backgrounds/" 2>/dev/null || true
  cp -f "$src/preview.png" "$dest/preview.png" 2>/dev/null || true
}
install_cursors() {
  local hc="$HOME/.local/share/icons/Prismatic-Shards" xc="$HOME/.icons/Prismatic-Shards"
  log_info "Installing hyprcursor -> $hc"
  mkdir -p "$hc" "$xc/cursors"
  cp -rf "$SCRIPT_DIR/cursor/hyprcursor/Prismatic-Shards/"* "$hc/"
  cp -rf "$SCRIPT_DIR/cursor/xcursor/Prismatic-Shards/32/"*.png "$xc/cursors/" 2>/dev/null || true
  printf '[Icon Theme]\nName=Prismatic-Shards\nComment=Fractured light. Unified system.\n' > "$xc/index.theme"
  log_info "Cursor installed. Enable: hyprctl setcursor Prismatic-Shards 32"
}
install_scripts() {
  mkdir -p "$HOME/.local/bin"
  cp -f "$SCRIPT_DIR/scripts/prismatic-shards-theme-toggle" "$HOME/.local/bin/"
  chmod +x "$HOME/.local/bin/prismatic-shards-theme-toggle"
  log_info "Installed toggle -> ~/.local/bin/prismatic-shards-theme-toggle"
}
install_dock() {
  mkdir -p "$HOME/.config/prismatic-shards"
  cp -f "$SCRIPT_DIR/extras/dock/dock.conf" "$HOME/.config/prismatic-shards/dock.conf"
  cp -f "$SCRIPT_DIR/extras/dock/launch-dock.sh" "$HOME/.config/prismatic-shards/launch-dock.sh"
  chmod +x "$HOME/.config/prismatic-shards/launch-dock.sh"
  log_info "Installed dock -> ~/.config/prismatic-shards/dock.conf"
}
apply_wallpaper() {
  local hero=""
  for c in "backgrounds/0-obsidian-glass.jpg" "backgrounds/1-refraction.jpg" "backgrounds/2-quiet-glass.jpg"; do
    [[ -f "$SCRIPT_DIR/$c" ]] && { hero="$SCRIPT_DIR/$c"; break; }
  done
  [[ -n "$hero" ]] || return 0
  mkdir -p "$HOME/.local/state/omarchy/current"
  ln -sfn "$hero" "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true
  log_info "Wallpaper linked -> $hero"
  if command -v swww >/dev/null 2>&1; then
    swww img "$hero" --transition-type grow --transition-pos 0.76,0.14 --transition-duration 1.2 2>/dev/null || true
  elif command -v hyprctl >/dev/null 2>&1; then
    hyprctl hyprpaper wallpaper ",$hero" 2>/dev/null || true
  fi
}
main() {
  log_info "Prismatic Shards installer."
  check_files || { log_error "Preflight failed."; exit 1; }
  local base="$HOME/.config/omarchy/themes"
  if [[ $EUID -eq 0 && "$COPY_ONLY" != true ]]; then base="/usr/share/omarchy/themes"; fi
  install_theme_dir "$SCRIPT_DIR" "$base/$THEME_DARK" "$THEME_DARK (dark)"
  install_theme_dir "$SCRIPT_DIR/variants/light" "$base/$THEME_LIGHT" "$THEME_LIGHT (light)"
  install_cursors; install_scripts; install_dock; apply_wallpaper
  if command -v hyprctl >/dev/null 2>&1; then hyprctl setcursor Prismatic-Shards 32 2>/dev/null || true; fi
  log_info "Done. Activate: omarchy-theme-set $THEME_DARK | omarchy-theme-set $THEME_LIGHT"
  log_info "Toggle: prismatic-shards-theme-toggle | Dock: ~/.config/prismatic-shards/launch-dock.sh"
}
main "$@"
