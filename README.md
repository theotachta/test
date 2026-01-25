# Simple Game Launcher (Auto-Update Prototype)

This prototype launcher is a small Windows-only desktop app (Tkinter) that:

- Uses the launcher's folder as the install directory and expects `melba.exe` to
  live alongside the launcher.
- Checks a GitHub-hosted `manifest.json` for version and file hashes.
- Downloads only missing/changed files.
- Writes a local `version.txt`.
- Offers a main action button that switches between **Update** and **Play**.
- Uses a borderless, modern layout with a sidebar and multiple pages.

## Requirements

- Windows
- Python 3.10+ (Tkinter included with standard Python distribution)

## Quick Start

```bash
python launcher.py
```

On first launch, the app shows a quick setup prompt and guides you through:

1. Place `melba.exe` in the same folder as `launcher.py`.
2. Click **Validate Data**, then **Update** if needed.

The launcher also performs a startup check and will report if updates are
available without downloading until you click **Update**. It estimates the
download size when possible.

## Assets

Add your artwork files here to customize the look:

- `assets/wallpaper.png` (background image on the Game page)
- `assets/logo.png` (top-left logo in the title bar)

## Configuration

The launcher stores settings in `config.json` next to `launcher.py`. The
install location is fixed to the launcher's folder.

If you want to change which repository the launcher downloads from, update the
constants at the top of `launcher.py` (`REPO_OWNER`, `REPO_NAME`, `REPO_BRANCH`,
and `MANIFEST_PATH`).

## Manifest Format

Host a `manifest.json` in your GitHub repo (raw file access). Example:

```json
{
  "version": "1.0.1",
  "files": [
    { "path": "Game.exe", "sha256": "YOUR_SHA256_HASH" },
    { "path": "data/config.json", "sha256": "YOUR_SHA256_HASH" },
    { "path": "saves/keep.txt", "sha256": "IGNORED", "skip": true }
  ]
}
```

Hashing tips (PowerShell):

```powershell
Get-FileHash .\\Game.exe -Algorithm SHA256
```

## Notes

- This repo includes a sample `manifest.json` and `version.txt` (set to `1.0`) for
  testing the update flow.
- The Update/Play button is enabled only when the executable path exists and
  no update is required.
- The updater downloads files directly from:
  `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
