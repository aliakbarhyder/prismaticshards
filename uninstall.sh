#!/bin/bash
# Prismatic Shards Omarchy Theme Uninstaller
# Safe uninstallation script for Prismatic Shards theme
# Author: Ali Akbar Hyder
# License: Prismatic Shards Personal Use License

set -euo pipefail

# Color output for better user experience
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running as root (required for Omarchy)
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This uninstaller must be run as root (sudo)."
        log_error "Please run: sudo $0"
        exit 1
    fi
}

# Check if theme exists
check_theme_exists() {
    local theme_dir="$1"

    if [[ ! -d "$theme_dir" ]]; then
        log_error "Theme directory not found: $theme_dir"
        log_error "The Prismatic Shards theme may already be uninstalled or never installed."
        exit 1
    fi

    log_info "Found theme at: $theme_dir"
}

# Create backup before uninstallation
create_backup() {
    local theme_dir="$1"
    local backup_dir="/tmp/prismatic-shards-uninstall-backup-$(date +%Y%m%d-%H%M%S)"

    log_warn "Creating backup of theme files..."
    cp -r "$theme_dir" "$backup_dir" && log_info "Backup created at: $backup_dir"
}

# Remove theme files
remove_theme_files() {
    local theme_dir="$1"

    log_info "Removing Prismatic Shards theme files..."
    rm -rf "$theme_dir"
    log_info "Theme files removed successfully"
}

# Check for user customizations
check_user_customizations() {
    local theme_dir="$1"
    local config_dir="$HOME/.config/omarchy"

    if [[ -d "$config_dir" ]]; then
        log_warn "Checking for user customizations in Omarchy configuration..."

        # Check if user has applied this theme
        if [[ -f "$config_dir/current-theme" ]] && grep -q "prismatic-shards" "$config_dir/current-theme" 2>/dev/null; then
            log_warn "Theme is currently active in Omarchy configuration."
            log_warn "Please deactivate it first: omarchy theme disable prismatic-shards"
            log_warn "After deactivation, run this uninstaller again."
        fi
    fi
}

# Validate theme removal
validate_removal() {
    local theme_dir="$1"

    if [[ -d "$theme_dir" ]]; then
        log_error "Theme directory still exists after removal: $theme_dir"
        log_error "Please check for any leftover files."
        exit 1
    fi

    log_info "Theme removal validated successfully"
}

# Main uninstallation function
main() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local theme_name="prismatic-shards"
    local omarchy_themes_dir="/usr/share/omarchy/themes"
    local theme_path="$omarchy_themes_dir/$theme_name"

    log_info "Starting Prismatic Shards theme uninstallation..."

    # Safety checks
    check_root
    check_theme_exists "$theme_path"

    # Backup and remove
    create_backup "$theme_path"
    check_user_customizations "$theme_path"
    remove_theme_files "$theme_path"

    # Validate
    validate_removal "$theme_path"

    log_info ""
    log_info "✅ Prismatic Shards theme uninstalled successfully!"
    log_info ""
    log_info "If you wish to reinstall, run:"
    log_info "  sudo $script_dir/install.sh"
    log_info ""
    log_info "For more information, see README.md in the original theme directory."
}

# Run main function
main "$@"