# Simple Game Launcher (Auto-Update Prototype)

This prototype launcher is a small Windows-only desktop app (Tkinter) that:

- Lets a player pick an install folder and game executable.
- Checks a GitHub-hosted `manifest.json` for version and file hashes.
- Downloads only missing/changed files.
- Writes a local `version.txt`.
- Offers a **Play** button to launch the game.

## Requirements

- Windows
- Python 3.10+ (Tkinter included with standard Python distribution)

## Quick Start

```bash
python launcher.py
```

On first launch, the app shows a quick setup prompt and guides you through:

1. Choosing an install folder.
2. Choosing the game executable.
3. Clicking **Download/Update**.

## Configuration

The launcher stores settings in `config.json` next to `launcher.py`.

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
    { "path": "data/config.json", "sha256": "YOUR_SHA256_HASH" }
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
- The Play button is enabled only when the executable path exists.
- The updater downloads files directly from:
  `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
