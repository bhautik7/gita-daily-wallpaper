#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 https://<username>.github.io/<repo>" >&2
  exit 1
fi

PAGES_URL="${1%/}"
if [[ ! "$PAGES_URL" =~ ^https?:// ]]; then
  echo "Error: URL must start with http:// or https:// (got: $PAGES_URL)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATER_SCRIPT="${SCRIPT_DIR}/update_mac_wallpaper.sh"
SWIFT_SRC="${SCRIPT_DIR}/set_mac_wallpaper.swift"

if [[ ! -x "$UPDATER_SCRIPT" ]]; then
  chmod +x "$UPDATER_SCRIPT"
fi

CONFIG_DIR="${HOME}/.config/gita-wallpaper"
CONFIG_FILE="${CONFIG_DIR}/config"
STATE_DIR="${HOME}/.local/share/gita-wallpaper"
SET_BIN="${STATE_DIR}/set-wallpaper"
LOG_FILE="${STATE_DIR}/agent.log"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_LABEL="com.gita.daily-wallpaper"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${PLIST_LABEL}.plist"

mkdir -p "$CONFIG_DIR" "$STATE_DIR" "$LAUNCH_AGENTS_DIR"

printf 'GITA_PAGES_URL=%q\n' "$PAGES_URL" > "$CONFIG_FILE"

if [[ -f "$SWIFT_SRC" ]] && command -v swiftc >/dev/null 2>&1; then
  echo "Compiling native AppKit wallpaper setter..."
  swiftc -O "$SWIFT_SRC" -o "$SET_BIN"
fi

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${UPDATER_SCRIPT}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>1800</integer>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
</dict>
</plist>
EOF

echo "Applying today's wallpaper from $PAGES_URL..."
"$UPDATER_SCRIPT" --url "$PAGES_URL" --force

USER_UID="$(id -u)"
launchctl bootout "gui/${USER_UID}" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/${USER_UID}" "$PLIST_PATH"

echo "Installed LaunchAgent at: $PLIST_PATH"
