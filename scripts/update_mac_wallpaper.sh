#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CONFIG_FILE="${HOME}/.config/gita-wallpaper/config"
STATE_DIR="${HOME}/.local/share/gita-wallpaper"
LAST_DATE_FILE="${STATE_DIR}/.last_applied_date"
SET_BIN="${STATE_DIR}/set-wallpaper"
SWIFT_SRC="${SCRIPT_DIR}/set_mac_wallpaper.swift"

PAGES_URL="${GITA_PAGES_URL:-}"
LOCAL_FILE=""
FORCE=0
OFFLINE=0

usage() {
  cat <<'EOF'
Usage: update_mac_wallpaper.sh [--url <pages_url>] [--local <path_to_png>] [--force] [--offline]

Options:
  --url <pages_url>     Base GitHub Pages URL (e.g. https://user.github.io/gita-daily-wallpaper)
  --local <path_to_png> Apply a local PNG wallpaper instead of downloading/generating
  --force               Re-apply even if today's wallpaper was already applied
  --offline             Skip network download and generate today's wallpaper locally
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
    --offline)
      OFFLINE=1
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
TMP_GEN_DIR="$(mktemp -d "${STATE_DIR}/tmp-gen.XXXXXX")"
cleanup() {
  rm -f "$TMP_FILE"
  rm -rf "$TMP_GEN_DIR"
}
trap cleanup EXIT

is_valid_png() {
  local file_path="$1"
  [[ -s "$file_path" ]] || return 1
  local magic_hex
  magic_hex="$(od -An -tx1 -N4 "$file_path" | tr -d ' \n')"
  [[ "$magic_hex" == "89504e47" ]]
}

generate_local_mac_png() {
  local python_bin=""
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    python_bin="${REPO_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    python_bin="$(command -v python3)"
  else
    echo "Error: No Python interpreter available for local wallpaper fallback." >&2
    return 1
  fi

  "$python_bin" "${REPO_ROOT}/src/generate.py" \
    --out "$TMP_GEN_DIR" \
    --date "$TODAY" \
    --only-mac >/dev/null
  cp "${TMP_GEN_DIR}/mac.png" "$TMP_FILE"
}

SOURCE_MODE="local-fallback"
if [[ -n "$LOCAL_FILE" ]]; then
  if [[ ! -f "$LOCAL_FILE" ]]; then
    echo "Error: Local PNG not found: $LOCAL_FILE" >&2
    exit 1
  fi
  cp "$LOCAL_FILE" "$TMP_FILE"
  SOURCE_MODE="local-file"
else
  DOWNLOADED=0
  if [[ "$OFFLINE" -eq 0 && -n "$PAGES_URL" ]]; then
    IMAGE_URL="${PAGES_URL%/}/daily/mac-${TODAY}.png"
    if curl -fsSL --retry 2 --max-time 20 "$IMAGE_URL" -o "$TMP_FILE" 2>/dev/null && is_valid_png "$TMP_FILE"; then
      DOWNLOADED=1
      SOURCE_MODE="remote:${IMAGE_URL}"
    fi
  fi

  if [[ "$DOWNLOADED" -eq 0 ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Remote daily/mac-${TODAY}.png unavailable; generating locally."
    generate_local_mac_png
    SOURCE_MODE="local-generated"
  fi
fi

if ! is_valid_png "$TMP_FILE"; then
  echo "Error: Prepared wallpaper file is not a valid PNG." >&2
  exit 1
fi

TS="$(date +%Y%m%d-%H%M%S)"
TARGET_FILE="${STATE_DIR}/mac-${TODAY}-${TS}.png"
mv "$TMP_FILE" "$TARGET_FILE"
chmod 644 "$TARGET_FILE"

if [[ -f "$SWIFT_SRC" ]] && command -v swiftc >/dev/null 2>&1; then
  if [[ ! -x "$SET_BIN" || "$SWIFT_SRC" -nt "$SET_BIN" ]]; then
    swiftc -O "$SWIFT_SRC" -o "$SET_BIN"
  fi
fi

if [[ -x "$SET_BIN" ]]; then
  "$SET_BIN" "$TARGET_FILE"
else
  osascript -e "tell application \"System Events\" to tell every desktop to set picture to POSIX file \"${TARGET_FILE}\""
fi

printf '%s\n' "$TODAY" > "$LAST_DATE_FILE"

sleep 2
for existing in "${STATE_DIR}"/mac-*.png; do
  [[ -e "$existing" ]] || continue
  if [[ "$existing" != "$TARGET_FILE" ]]; then
    rm -f "$existing"
  fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Applied Mac wallpaper (${SOURCE_MODE}): $TARGET_FILE"
