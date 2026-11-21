# Daily Bhagavad Gita Wallpaper

Minimalist dark daily wallpapers for **iPhone** (`1290×2796`) and **MacBook** (`3456×2234`), displaying one new 1-sentence practical learning from the Bhagavad Gita each day for 24 hours with zero clutter.

- **365 curated daily learnings** spanning all 18 chapters (`data/lessons.json`)
- **Automated daily build** via GitHub Actions & GitHub Pages (at ~12:15 AM `America/Toronto`)
- **Ultra-minimal design**: deep charcoal/midnight vignette, subtle warm gold hairline, warm cream balanced serif typography, no citation clutter

---

## Step 1: Push to GitHub & Enable GitHub Pages

1. Create a public GitHub repository and push this folder:

   ```bash
   cd gita-daily-wallpaper
   git add .
   git commit -m "Initial daily Bhagavad Gita wallpaper generator"
   gh repo create gita-daily-wallpaper --public --source=. --remote=origin --push
   ```

   *(GitHub Pages works free on public repositories. If you use GitHub Pro/Team on a private repo, pass `--private` instead.)*

2. Enable GitHub Pages in your repository on GitHub:
   - Open **Settings → Pages**
   - Under **Build and deployment → Source**, choose **GitHub Actions**
   - Trigger **Actions → Daily Gita Wallpaper → Run workflow** once (or wait a minute after pushing `main`)

Your daily wallpapers will be live at:
- Preview site: `https://<username>.github.io/gita-daily-wallpaper/`
- iPhone image: `https://<username>.github.io/gita-daily-wallpaper/iphone.png`
- MacBook image: `https://<username>.github.io/gita-daily-wallpaper/mac.png`

---

## Step 2: iPhone Setup (60-Second Apple Shortcut Automation)

Set up a daily personal automation on your iPhone so it pulls the fresh wallpaper each morning and keeps it on your screen for 24 hours:

1. Open the **Shortcuts** app → **Automation** tab → tap **`+`** (Create Personal Automation).
2. Choose **Time of Day** → set e.g. **6:00 AM**, **Daily**, and select **Run Immediately** (turn off *Notify When Run* if you want silent swaps).
3. Tap **New Blank Automation** and add these actions in order:
   1. **Date** *(Current Date)*
   2. **Format Date** → Date Format: **Custom**, Format String: `yyyy-MM-dd` *(cache-buster so iOS fetches today's fresh image)*
   3. **URL** → `https://<username>.github.io/gita-daily-wallpaper/iphone.png?d=` followed by the **Formatted Date** variable
   4. **Get Contents of URL** *(downloads today's PNG)*
   5. **Set Wallpaper Photo**:
      - Target **Lock Screen** (and/or **Home Screen**)
      - Expand the small arrow (`>`) on **Set Wallpaper Photo** and turn **OFF**:
        - **Show Preview** *(critical for unattended background updates)*
        - **Crop to Subject** *(preserves exact centering below the clock)*
4. Tap **Done** and press the **Play** button once to test it immediately.

---

## Step 3: MacBook Setup (1-Command Auto-Updater)

Install the lightweight macOS `LaunchAgent` so your MacBook updates automatically each day (and catches up immediately if it was asleep overnight):

```bash
./scripts/install_mac_agent.sh https://<username>.github.io/gita-daily-wallpaper
```

### Helpful Local Commands

- **Test locally before pushing to GitHub:**
  ```bash
  ./scripts/update_mac_wallpaper.sh --local dist/mac.png --force
  ```
- **Force re-fetch from GitHub Pages anytime:**
  ```bash
  ./scripts/update_mac_wallpaper.sh --force
  ```
- **Uninstall the MacBook background updater:**
  ```bash
  ./scripts/uninstall_mac_agent.sh
  ```

---

## Customization

- **Text placement / dimensions / colors:** edit [`config.json`](config.json).
- **Show Chapter & Verse citation:** set `"show_citation": true` in `config.json` (or pass `--show-citation`).
- **Custom serif font:** drop any `.ttf` or `.otf` font file into `assets/fonts/` and it will automatically take priority.
- **Test a specific future date locally:**
  ```bash
  .venv/bin/python src/generate.py --out dist --date 2026-12-01
  ```
