#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${HOME}/.config/gita-wallpaper/config"
STATE_DIR="${HOME}/.local/share/gita-wallpaper"
LAST_DATE_FILE="${STATE_DIR}/.last_applied_date"

PAGES_URL="${GITA_PAGES_URL:-}"
LOCAL_FILE=""
FORCE=0

usage() {
  cat <<'EOF'
Usage: update_mac_wallpaper.sh [--url <pages_url>] [--local <path_to_png>] [--force]

Options:
  --url <pages_url>     Base GitHub Pages URL (e.g. https://user.github.io/gita-daily-wallpaper)
  --local <path_to_png> Apply a local PNG wallpaper instead of downloading from GitHub Pages
  --force               Re-apply even if today's wallpaper was already applied
  -h, --help            Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      if [[ $# -lt 2 ]]; then
        echo "Error: --url requires an argument." >&2
        exit 1
      fi
      PAGES_URL="$2"
      shift 2
      ;;
    --local)
      if [[ $# -lt 2 ]]; then
        echo "Error: --local requires an argument." >&2
        exit 1
      fi
      LOCAL_FILE="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

mkdir -p "$STATE_DIR"

TODAY="$(date +%Y-%m-%d)"
if [[ "$FORCE" -eq 0 && -f "$LAST_DATE_FILE" ]]; then
  LAST_APPLIED="$(tr -d '[:space:]' < "$LAST_DATE_FILE")"
  if [[ "$LAST_APPLIED" == "$TODAY" ]]; then
    exit 0
  fi
fi

if [[ -z "$LOCAL_FILE" && -z "$PAGES_URL" && -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  PAGES_URL="${GITA_PAGES_URL:-}"
fi

TMP_FILE="$(mktemp "${STATE_DIR}/tmp-mac.XXXXXX")"
cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

if [[ -n "$LOCAL_FILE" ]]; then
  if [[ ! -f "$LOCAL_FILE" ]]; then
    echo "Error: Local PNG not found: $LOCAL_FILE" >&2
    exit 1
  fi
  cp "$LOCAL_FILE" "$TMP_FILE"
else
  if [[ -z "$PAGES_URL" ]]; then
    echo "Error: No Pages URL configured. Pass --url or set GITA_PAGES_URL in $CONFIG_FILE." >&2
    exit 1
  fi
  IMAGE_URL="${PAGES_URL%/}/mac.png?d=${TODAY}"
  curl -fsSL --retry 2 --max-time 20 "$IMAGE_URL" -o "$TMP_FILE"
fi

# Verify PNG magic header (89 50 4e 47).
MAGIC_HEX="$(od -An -tx1 -N4 "$TMP_FILE" | tr -d ' \n')"
if [[ "$MAGIC_HEX" != "89504e47" ]]; then
  echo "Error: Downloaded or provided file is not a valid PNG (header: $MAGIC_HEX)." >&2
  exit 1
fi

TS="$(date +%Y%m%d-%H%M%S)"
TARGET_FILE="${STATE_DIR}/mac-${TODAY}-${TS}.png"
mv "$TMP_FILE" "$TARGET_FILE"
chmod 644 "$TARGET_FILE"

osascript -e "tell application \"System Events\" to tell every desktop to set picture to POSIX file \"${TARGET_FILE}\""

printf '%s\n' "$TODAY" > "$LAST_DATE_FILE"

sleep 2
for existing in "${STATE_DIR}"/mac-*.png; do
  [[ -e "$existing" ]] || continue
  if [[ "$existing" != "$TARGET_FILE" ]]; then
    rm -f "$existing"
  fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Applied Mac wallpaper: $TARGET_FILE"
