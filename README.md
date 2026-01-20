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

## Configuration

The launcher stores settings in `config.json` next to `launcher.py`.

Fields:

- `repo_owner`
- `repo_name`
- `repo_branch`
- `manifest_path`

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

- The Play button is enabled only when the executable path exists.
- The updater downloads files directly from:
  `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
