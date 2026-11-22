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
- Preview site & 1-tap iPhone Shortcut installer: `https://<username>.github.io/gita-daily-wallpaper/`
- iPhone image (JPEG / PNG): `https://<username>.github.io/gita-daily-wallpaper/iphone.jpg` / `iphone.png`
- MacBook image: `https://<username>.github.io/gita-daily-wallpaper/mac.png`

---

## Step 2: iPhone Setup (1-Tap Shortcut + Daily Automation)

Install the pre-built **Daily Gita Wallpaper** shortcut (which automatically downloads `iphone.jpg`, saves it to Photos, and sets your Lock Screen without showing any error or prompt):

1. Open **`https://<username>.github.io/gita-daily-wallpaper/`** in **Safari on your iPhone**.
2. Tap **Install iPhone Shortcut** → **Add Shortcut**.
3. Open **Shortcuts**, tap **Daily Gita Wallpaper** once to test (allow Photos/website permission if asked; if prompted for a wallpaper, choose a **Photo** Lock Screen).
4. Schedule it to run automatically every day:
   - Open **Shortcuts** → **Automation** tab → tap **`+`**
   - Choose **Time of Day** (e.g., **6:00 AM**, **Daily**) → select **Run Immediately** (turn *Notify When Run* OFF) → tap **Next**
   - Pick **Daily Gita Wallpaper** from your shortcuts list

*(Optional: to keep downloaded wallpapers out of your main Recents feed, create a Photos album such as `Gita`, open the **Daily Gita Wallpaper** shortcut, and change `Recents` in **Save to Photo Album** to your album.)*

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
