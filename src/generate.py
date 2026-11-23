#!/usr/bin/env python3
"""Generate daily minimalist Bhagavad Gita wallpapers and static preview site."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import html
import json
from pathlib import Path
import random
import shutil
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYSTEM_FONT_CANDIDATES: tuple[tuple[Path, int], ...] = (
    (Path("/usr/share/fonts/truetype/ebgaramond/EBGaramond-Regular.ttf"), 0),
    (Path("/usr/share/fonts/truetype/ebgaramond/EBGaramond12-Regular.ttf"), 0),
    (Path("/System/Library/Fonts/Supplemental/Baskerville.ttc"), 0),
    (Path("/System/Library/Fonts/Supplemental/Georgia.ttf"), 0),
    (Path("/System/Library/Fonts/NewYork.ttf"), 0),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"), 0),
)

_BACKGROUND_CACHE: dict[tuple[int, int, float, str, str], Image.Image] = {}


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a #RRGGBB hex string into an (R, G, B) tuple."""
    stripped = color.lstrip("#")
    if len(stripped) != 6:
        raise ValueError(f"Expected #RRGGBB color, got: {color!r}")
    return (
        int(stripped[0:2], 16),
        int(stripped[2:4], 16),
        int(stripped[4:6], 16),
    )


def resolve_target_date(date_str: str | None, timezone_name: str) -> date:
    """Resolve the target calendar date from an explicit ISO string or timezone."""
    if date_str:
        return date.fromisoformat(date_str)
    from datetime import datetime

    return datetime.now(ZoneInfo(timezone_name)).date()


def select_lesson(
    lessons: list[dict],
    target_date: date,
    start_date_str: str,
) -> tuple[int, dict]:
    """Select today's lesson deterministically using date delta modulo lesson count."""
    if not lessons:
        raise ValueError("Lessons list must not be empty.")
    start_date = date.fromisoformat(start_date_str)
    day_index = (target_date - start_date).days % len(lessons)
    return day_index, lessons[day_index]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the highest-priority serif font available on the host."""
    custom_fonts_dir = PROJECT_ROOT / "assets" / "fonts"
    if custom_fonts_dir.is_dir():
        for ext in ("*.ttf", "*.otf", "*.ttc"):
            for font_path in sorted(custom_fonts_dir.glob(ext)):
                try:
                    return ImageFont.truetype(str(font_path), size=size, index=0)
                except OSError:
                    continue

    for font_path, face_index in SYSTEM_FONT_CANDIDATES:
        if font_path.is_file():
            try:
                return ImageFont.truetype(str(font_path), size=size, index=face_index)
            except OSError:
                continue

    return ImageFont.load_default()


def _create_monochrome_dither_tiles(
    width: int,
    height: int,
    seed: int,
    amplitude: int = 2,
) -> tuple[Image.Image, Image.Image]:
    """Create deterministic ±amplitude monochrome dither images via fast tiling."""
    tile_w, tile_h = 251, 257
    rng = random.Random(seed)
    pos_bytes = bytearray(tile_w * tile_h)
    neg_bytes = bytearray(tile_w * tile_h)

    for idx in range(tile_w * tile_h):
        delta = rng.randint(-amplitude, amplitude)
        if delta > 0:
            pos_bytes[idx] = delta
        elif delta < 0:
            neg_bytes[idx] = -delta

    pos_tile = Image.frombytes("L", (tile_w, tile_h), bytes(pos_bytes))
    neg_tile = Image.frombytes("L", (tile_w, tile_h), bytes(neg_bytes))

    pos_canvas = Image.new("L", (width, height))
    neg_canvas = Image.new("L", (width, height))
    for y in range(0, height, tile_h):
        for x in range(0, width, tile_w):
            pos_canvas.paste(pos_tile, (x, y))
            neg_canvas.paste(neg_tile, (x, y))

    return pos_canvas.convert("RGB"), neg_canvas.convert("RGB")


def render_background(
    width: int,
    height: int,
    theme: dict,
    center_y_ratio: float = 0.5,
) -> Image.Image:
    """Render a smooth radial dark gradient background with subtle anti-banding dither."""
    outer_r, outer_g, outer_b = hex_to_rgb(theme["bg_outer"])
    center_r, center_g, center_b = hex_to_rgb(theme["bg_center"])

    scale = 8
    sw = max(16, width // scale)
    sh = max(16, height // scale)

    cx = sw * 0.5
    cy = sh * center_y_ratio
    rx = sw * 0.62
    ry = sh * 0.58

    buf = bytearray(sw * sh * 3)
    pos = 0
    for y in range(sh):
        dy = (y - cy) / ry
        dy2 = dy * dy
        for x in range(sw):
            dx = (x - cx) / rx
            dist = (dx * dx + dy2) ** 0.5
            t = min(1.0, dist)
            # Smoothstep curve for gentle atmospheric falloff without hard halo edges.
            smooth_t = t * t * (3.0 - 2.0 * t)
            inv_t = 1.0 - smooth_t
            buf[pos] = int(outer_r + (center_r - outer_r) * inv_t + 0.5)
            buf[pos + 1] = int(outer_g + (center_g - outer_g) * inv_t + 0.5)
            buf[pos + 2] = int(outer_b + (center_b - outer_b) * inv_t + 0.5)
            pos += 3

    low_res = Image.frombytes("RGB", (sw, sh), bytes(buf))
    base = low_res.resize((width, height), resample=Image.Resampling.BICUBIC)

    seed = (width * 10007) ^ (height * 65521)
    pos_dither, neg_dither = _create_monochrome_dither_tiles(width, height, seed=seed, amplitude=2)
    base = ImageChops.add(base, pos_dither)
    base = ImageChops.subtract(base, neg_dither)
    return base


def wrap_balanced(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: float,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Wrap words into minimum lines while balancing line widths via dynamic programming."""
    words = text.split()
    if not words:
        return [""]

    n = len(words)
    # dp[i] = (num_lines, total_cost, next_break_index)
    dp: list[tuple[int, float, int]] = [(0, 0.0, n)] * (n + 1)
    dp[n] = (0, 0.0, n)

    for i in range(n - 1, -1, -1):
        best: tuple[int, float, int] | None = None
        for j in range(i + 1, n + 1):
            candidate = " ".join(words[i:j])
            line_w = draw.textlength(candidate, font=font)
            if line_w > max_width and j > i + 1:
                break

            if line_w > max_width:
                line_cost = 1000.0 + ((line_w - max_width) / max_width) ** 2
            else:
                slack_ratio = (max_width - line_w) / max_width
                line_cost = slack_ratio * slack_ratio

            # Penalize leaving a tiny lone orphan word on the final line.
            if j == n and (j - i) == 1 and n > 1 and line_w < 0.28 * max_width:
                line_cost += 0.25

            next_lines, next_cost, _ = dp[j]
            option = (1 + next_lines, line_cost + next_cost, j)
            if best is None or (option[0], option[1]) < (best[0], best[1]):
                best = option

        assert best is not None
        dp[i] = best

    lines: list[str] = []
    idx = 0
    while idx < n:
        _, _, next_idx = dp[idx]
        lines.append(" ".join(words[idx:next_idx]))
        idx = next_idx
    return lines


def _fit_typography(
    text: str,
    device_cfg: dict,
    draw: ImageDraw.ImageDraw,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, int, list[str]]:
    """Choose the largest font size within bounds that satisfies max_lines and max_width."""
    max_width = device_cfg["width"] * device_cfg["max_width_ratio"]
    base_size = int(device_cfg["base_font_size"])
    min_size = int(device_cfg["min_font_size"])
    max_lines = int(device_cfg["max_lines"])

    chosen_font = load_font(min_size)
    chosen_size = min_size
    chosen_lines = wrap_balanced(text, chosen_font, max_width, draw)

    for size in range(base_size, min_size - 1, -2):
        font = load_font(size)
        lines = wrap_balanced(text, font, max_width, draw)
        fits_width = all(draw.textlength(line, font=font) <= max_width for line in lines)
        if len(lines) <= max_lines and fits_width:
            return font, size, lines
        chosen_font, chosen_size, chosen_lines = font, size, lines

    return chosen_font, chosen_size, chosen_lines


def render_wallpaper(
    lesson_text: str,
    device_cfg: dict,
    theme: dict,
    citation: str | None = None,
) -> Image.Image:
    """Render a minimalist dark wallpaper with balanced cream typography and gold hairline."""
    width = int(device_cfg["width"])
    height = int(device_cfg["height"])
    center_y_ratio = float(device_cfg["center_y_ratio"])
    rule_width = int(device_cfg["rule_width"])

    cache_key = (width, height, center_y_ratio, theme["bg_outer"], theme["bg_center"])
    cached_bg = _BACKGROUND_CACHE.get(cache_key)
    if cached_bg is None:
        cached_bg = render_background(width, height, theme, center_y_ratio=center_y_ratio)
        _BACKGROUND_CACHE[cache_key] = cached_bg
    canvas = cached_bg.copy()
    draw = ImageDraw.Draw(canvas)

    font, font_size, lines = _fit_typography(lesson_text, device_cfg, draw)
    line_step = round(font_size * 1.48)
    rule_height = 2
    rule_gap = round(font_size * 0.75)

    # Measure visual glyph bounds of the first and last lines so vertical centering is exact.
    first_bbox = draw.textbbox((0, 0), lines[0], font=font)
    last_bbox = draw.textbbox((0, 0), lines[-1], font=font)
    text_block_height = ((len(lines) - 1) * line_step) + (last_bbox[3] - first_bbox[1])

    center_x = width / 2.0
    center_y = height * center_y_ratio

    citation_font = None
    citation_gap = 0
    citation_height = 0
    if citation:
        citation_size = max(24, round(font_size * 0.42))
        citation_font = load_font(citation_size)
        citation_gap = round(font_size * 0.85)
        cit_bbox = draw.textbbox((0, 0), citation, font=citation_font)
        citation_height = cit_bbox[3] - cit_bbox[1]

    total_content_height = text_block_height + (citation_gap + citation_height if citation else 0)
    first_visual_top = center_y - (total_content_height / 2.0)
    first_draw_y = first_visual_top - first_bbox[1]

    # Composite the subtle gold hairline above the text block on an RGBA overlay.
    accent_rgb = hex_to_rgb(theme["accent"])
    accent_alpha = max(0, min(255, round(float(theme.get("accent_opacity", 0.45)) * 255)))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    rule_y = round(first_visual_top - rule_gap - rule_height)
    rule_x0 = round(center_x - (rule_width / 2.0))
    rule_x1 = rule_x0 + rule_width
    overlay_draw.rectangle(
        [rule_x0, rule_y, rule_x1, rule_y + rule_height - 1],
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], accent_alpha),
    )

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    text_rgb = hex_to_rgb(theme["text"])
    for idx, line in enumerate(lines):
        line_w = draw.textlength(line, font=font)
        line_x = center_x - (line_w / 2.0)
        line_y = first_draw_y + (idx * line_step)
        draw.text((line_x, line_y), line, font=font, fill=text_rgb)

    if citation and citation_font is not None:
        cit_bbox = draw.textbbox((0, 0), citation, font=citation_font)
        cit_w = draw.textlength(citation, font=citation_font)
        cit_visual_top = first_visual_top + text_block_height + citation_gap
        cit_draw_y = cit_visual_top - cit_bbox[1]
        cit_color = (
            round(accent_rgb[0] * 0.85 + text_rgb[0] * 0.15),
            round(accent_rgb[1] * 0.85 + text_rgb[1] * 0.15),
            round(accent_rgb[2] * 0.85 + text_rgb[2] * 0.15),
        )
        draw.text((center_x - (cit_w / 2.0), cit_draw_y), citation, font=citation_font, fill=cit_color)

    return canvas


def build_index_html(today_payload: dict, has_shortcut: bool = False) -> str:
    """Build a minimalist dark static preview page for today's wallpapers."""
    safe_lesson = html.escape(today_payload["lesson"])
    safe_date = html.escape(today_payload["date"])
    day_num = int(today_payload["day_index"]) + 1
    total = int(today_payload["total_lessons"])

    shortcut_block = ""
    if has_shortcut:
        shortcut_block = """
      <div class="cta-wrap">
        <a class="cta" href="DailyGitaWallpaper.shortcut">Install iPhone Shortcut</a>
        <p class="cta-sub">Downloads today&rsquo;s wallpaper to Photos &amp; sets your Lock Screen automatically</p>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Daily Bhagavad Gita Wallpaper</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0a0b0f;
      --card: #13141b;
      --text: #f1ece2;
      --muted: #9b9589;
      --accent: #c8a96e;
      --border: rgba(200, 169, 110, 0.22);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at 50% 20%, #16151c 0%, var(--bg) 70%);
      color: var(--text);
      font-family: Georgia, "Times New Roman", serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 3rem 1.25rem 4rem;
    }}
    main {{
      width: 100%;
      max-width: 960px;
    }}
    header {{
      text-align: center;
      margin-bottom: 2.75rem;
    }}
    .meta {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 0.78rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 1.25rem;
    }}
    .rule {{
      width: 56px;
      height: 1px;
      background: var(--accent);
      opacity: 0.6;
      margin: 0 auto 1.5rem;
    }}
    blockquote {{
      margin: 0 auto;
      max-width: 680px;
      font-size: clamp(1.35rem, 2.8vw, 1.95rem);
      line-height: 1.5;
      font-weight: 400;
    }}
    .cta-wrap {{
      margin-top: 2rem;
    }}
    .cta {{
      display: inline-block;
      padding: 0.78rem 1.5rem;
      border-radius: 999px;
      border: 1px solid rgba(200, 169, 110, 0.55);
      background: rgba(200, 169, 110, 0.14);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 0.94rem;
      font-weight: 500;
      letter-spacing: 0.02em;
      text-decoration: none;
      transition: background 0.15s ease, border-color 0.15s ease;
    }}
    .cta:hover {{
      background: rgba(200, 169, 110, 0.24);
      border-color: var(--accent);
    }}
    .cta-sub {{
      margin: 0.65rem auto 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 0.82rem;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.5rem;
      align-items: start;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.15rem;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.9rem;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 0.88rem;
    }}
    .card-header span {{ color: var(--muted); }}
    .card-header a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .card-header a:hover {{ text-decoration: underline; }}
    .preview {{
      display: block;
      width: 100%;
      height: auto;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }}
    footer {{
      margin-top: 2.5rem;
      text-align: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="meta">{safe_date} &middot; Day {day_num} of {total}</div>
      <div class="rule"></div>
      <blockquote>{safe_lesson}</blockquote>{shortcut_block}
    </header>
    <section class="grid">
      <div class="card">
        <div class="card-header">
          <span>iPhone &middot; 1290&times;2796</span>
          <span class="links"><a href="iphone.jpg">iphone.jpg</a> &middot; <a href="iphone.png">iphone.png</a></span>
        </div>
        <a href="iphone.jpg"><img class="preview" src="iphone.png" alt="iPhone daily wallpaper preview" /></a>
      </div>
      <div class="card">
        <div class="card-header">
          <span>MacBook &middot; 3456&times;2234</span>
          <a href="mac.png">mac.png</a>
        </div>
        <a href="mac.png"><img class="preview" src="mac.png" alt="MacBook daily wallpaper preview" /></a>
      </div>
    </section>
    <footer>
      API feed: <a href="today.json">today.json</a>
    </footer>
  </main>
</body>
</html>
"""


def generate_site(
    out_dir: Path,
    config_path: Path,
    lessons_path: Path,
    date_str: str | None = None,
    tz_override: str | None = None,
    show_citation_override: bool | None = None,
    only_mac: bool = False,
    buffer_days: int = 35,
) -> dict:
    """Generate wallpapers, today.json, index.html, and .nojekyll into out_dir."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))

    timezone_name = tz_override or config["timezone"]
    target_date = resolve_target_date(date_str, timezone_name)
    day_index, entry = select_lesson(lessons, target_date, config["start_date"])

    show_citation = (
        bool(config.get("show_citation", False))
        if show_citation_override is None
        else show_citation_override
    )

    def _citation_for(item: dict) -> str | None:
        return f"Bhagavad Gita {item['chapter']}.{item['verse']}" if show_citation else None

    out_dir.mkdir(parents=True, exist_ok=True)
    theme = config["theme"]

    if only_mac:
        mac_img = render_wallpaper(
            lesson_text=entry["lesson"],
            device_cfg=config["devices"]["mac"],
            theme=theme,
            citation=_citation_for(entry),
        )
        mac_img.save(out_dir / "mac.png", format="PNG", optimize=True)
        return {
            "date": target_date.isoformat(),
            "day_index": day_index,
            "total_lessons": len(lessons),
            "lesson": entry["lesson"],
            "mac_image": "mac.png",
        }

    rendered_today: dict[str, Image.Image] = {}
    for device_name, filename in (("iphone", "iphone.png"), ("mac", "mac.png")):
        img = render_wallpaper(
            lesson_text=entry["lesson"],
            device_cfg=config["devices"][device_name],
            theme=theme,
            citation=_citation_for(entry),
        )
        rendered_today[device_name] = img
        img.save(out_dir / filename, format="PNG", optimize=True)
        if device_name == "iphone":
            img.save(
                out_dir / "iphone.jpg",
                format="JPEG",
                quality=95,
                subsampling=0,
                optimize=True,
            )

    if buffer_days > 0:
        daily_dir = out_dir / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        mac_buffer_end = min(14, buffer_days)
        for offset in range(-1, buffer_days):
            buf_date = target_date + timedelta(days=offset)
            buf_iso = buf_date.isoformat()
            _, buf_entry = select_lesson(lessons, buf_date, config["start_date"])
            buf_citation = _citation_for(buf_entry)

            if offset == 0:
                iphone_buf_img = rendered_today["iphone"]
            else:
                iphone_buf_img = render_wallpaper(
                    lesson_text=buf_entry["lesson"],
                    device_cfg=config["devices"]["iphone"],
                    theme=theme,
                    citation=buf_citation,
                )
            iphone_buf_img.save(
                daily_dir / f"{buf_iso}.jpg",
                format="JPEG",
                quality=90,
                subsampling=0,
                optimize=True,
            )

            if offset < mac_buffer_end:
                if offset == 0:
                    shutil.copy2(out_dir / "mac.png", daily_dir / f"mac-{buf_iso}.png")
                else:
                    mac_buf_img = render_wallpaper(
                        lesson_text=buf_entry["lesson"],
                        device_cfg=config["devices"]["mac"],
                        theme=theme,
                        citation=buf_citation,
                    )
                    mac_buf_img.save(
                        daily_dir / f"mac-{buf_iso}.png",
                        format="PNG",
                        optimize=True,
                    )

    shortcut_src = PROJECT_ROOT / "assets" / "DailyGitaWallpaper.shortcut"
    has_shortcut = shortcut_src.is_file()
    if has_shortcut:
        shutil.copy2(shortcut_src, out_dir / "DailyGitaWallpaper.shortcut")

    today_payload = {
        "date": target_date.isoformat(),
        "day_index": day_index,
        "total_lessons": len(lessons),
        "lesson": entry["lesson"],
        "iphone_image": "iphone.png",
        "iphone_jpg": "iphone.jpg",
        "mac_image": "mac.png",
    }
    (out_dir / "today.json").write_text(
        json.dumps(today_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        build_index_html(today_payload, has_shortcut=has_shortcut),
        encoding="utf-8",
    )
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    return today_payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for wallpaper generation."""
    parser = argparse.ArgumentParser(description="Generate daily Bhagavad Gita wallpapers.")
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "dist",
        help="Output directory for generated assets (default: dist)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override target date as YYYY-MM-DD",
    )
    parser.add_argument(
        "--tz",
        type=str,
        default=None,
        help="Override IANA timezone from config.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config.json",
        help="Path to config.json",
    )
    parser.add_argument(
        "--lessons",
        type=Path,
        default=PROJECT_ROOT / "data" / "lessons.json",
        help="Path to lessons.json",
    )
    parser.add_argument(
        "--show-citation",
        action="store_true",
        default=None,
        help="Render Chapter.Verse citation beneath the learning sentence",
    )
    parser.add_argument(
        "--only-mac",
        action="store_true",
        help="Render only mac.png for fast local desktop updates",
    )
    parser.add_argument(
        "--buffer-days",
        type=int,
        default=35,
        help="Pre-generate N future days into out/daily/ (default: 35, 0 disables)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    payload = generate_site(
        out_dir=args.out,
        config_path=args.config,
        lessons_path=args.lessons,
        date_str=args.date,
        tz_override=args.tz,
        show_citation_override=args.show_citation,
        only_mac=args.only_mac,
        buffer_days=args.buffer_days,
    )
    print(f"Generated wallpapers for {payload['date']} (day {payload['day_index'] + 1}/{payload['total_lessons']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
