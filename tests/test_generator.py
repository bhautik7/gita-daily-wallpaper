from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generate import (  # noqa: E402
    generate_site,
    load_font,
    resolve_target_date,
    select_lesson,
    wrap_balanced,
)


def test_lessons_dataset_integrity() -> None:
    lessons = json.loads((PROJECT_ROOT / "data" / "lessons.json").read_text(encoding="utf-8"))
    assert len(lessons) == 365

    ids = [entry["id"] for entry in lessons]
    assert ids == list(range(1, 366))

    chapters = {entry["chapter"] for entry in lessons}
    assert chapters == set(range(1, 19))

    normalized = []
    for entry in lessons:
        text = entry["lesson"]
        assert isinstance(text, str)
        assert "\n" not in text
        assert "\r" not in text
        assert 25 <= len(text) <= 135, f"Unexpected length on id={entry['id']}: {len(text)}"
        assert text[-1] in ".!?", f"Missing terminal punctuation on id={entry['id']}: {text!r}"
        normalized.append(" ".join(text.lower().split()))

    assert len(normalized) == len(set(normalized)), "Duplicate normalized lessons found"


def test_deterministic_rotation_and_wraparound() -> None:
    lessons = json.loads((PROJECT_ROOT / "data" / "lessons.json").read_text(encoding="utf-8"))
    start_date = "2026-11-21"

    idx_day0, entry_day0 = select_lesson(lessons, date(2026, 11, 21), start_date)
    idx_day1, entry_day1 = select_lesson(lessons, date(2026, 11, 22), start_date)
    idx_wrap, entry_wrap = select_lesson(lessons, date(2027, 11, 21), start_date)

    assert idx_day0 == 0
    assert idx_day1 == 1
    assert entry_day0["id"] != entry_day1["id"]
    assert idx_wrap == 0
    assert entry_wrap == entry_day0

    resolved_explicit = resolve_target_date("2026-12-01", "America/Toronto")
    assert resolved_explicit == date(2026, 12, 1)

    resolved_tz = resolve_target_date(None, "America/Toronto")
    assert isinstance(resolved_tz, date)


def test_balanced_wrapping_fits_width_and_preserves_words() -> None:
    canvas = Image.new("RGB", (1290, 2796))
    draw = ImageDraw.Draw(canvas)
    font = load_font(58)
    max_width = 1290 * 0.74

    lessons = json.loads((PROJECT_ROOT / "data" / "lessons.json").read_text(encoding="utf-8"))
    for entry in lessons[:30]:
        lines = wrap_balanced(entry["lesson"], font, max_width, draw)
        assert len(lines) >= 1
        assert " ".join(lines).split() == entry["lesson"].split()
        for line in lines:
            assert draw.textlength(line, font=font) <= max_width


def test_end_to_end_generation(tmp_path: Path) -> None:
    payload = generate_site(
        out_dir=tmp_path,
        config_path=PROJECT_ROOT / "config.json",
        lessons_path=PROJECT_ROOT / "data" / "lessons.json",
        date_str="2026-11-21",
    )

    assert payload["date"] == "2026-11-21"
    assert payload["day_index"] == 0
    assert payload["total_lessons"] == 365
    assert payload["iphone_image"] == "iphone.png"
    assert payload["mac_image"] == "mac.png"

    iphone_path = tmp_path / "iphone.png"
    mac_path = tmp_path / "mac.png"
    today_path = tmp_path / "today.json"
    index_path = tmp_path / "index.html"
    nojekyll_path = tmp_path / ".nojekyll"

    assert iphone_path.is_file()
    assert mac_path.is_file()
    assert today_path.is_file()
    assert index_path.is_file()
    assert nojekyll_path.is_file()

    with Image.open(iphone_path) as iphone_img:
        assert iphone_img.size == (1290, 2796)
        assert iphone_img.mode == "RGB"
        # Check center text band around 53% height has bright cream pixels rendered.
        crop = iphone_img.crop((150, int(2796 * 0.44), 1140, int(2796 * 0.62)))
        extrema = crop.getextrema()
        assert all(hi - lo > 120 for lo, hi in extrema), "Expected text contrast in iPhone center band"

    with Image.open(mac_path) as mac_img:
        assert mac_img.size == (3456, 2234)
        assert mac_img.mode == "RGB"
        crop = mac_img.crop((700, int(2234 * 0.38), 2756, int(2234 * 0.58)))
        extrema = crop.getextrema()
        assert all(hi - lo > 120 for lo, hi in extrema), "Expected text contrast in Mac center band"

    today_json = json.loads(today_path.read_text(encoding="utf-8"))
    assert today_json == payload

    html_text = index_path.read_text(encoding="utf-8")
    assert payload["lesson"] in html_text
    assert "iphone.png" in html_text
    assert "mac.png" in html_text
