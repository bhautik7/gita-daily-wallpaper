#!/usr/bin/env bash
set -euo pipefail

PLIST_LABEL="com.gita.daily-wallpaper"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"
USER_UID="$(id -u)"

if [[ -f "$PLIST_PATH" ]]; then
  launchctl bootout "gui/${USER_UID}" "$PLIST_PATH" 2>/dev/null || true
  rm -f "$PLIST_PATH"
  echo "Removed LaunchAgent: $PLIST_PATH"
else
  echo "LaunchAgent not found at: $PLIST_PATH"
fi
