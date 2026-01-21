import hashlib
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.error import URLError
from urllib.request import urlopen

APP_TITLE = "Game Launcher"
DEFAULT_CONFIG = {
    "install_dir": "",
    "game_exe": "",
}
REPO_OWNER = "your-org"
REPO_NAME = "your-game-repo"
REPO_BRANCH = "main"
MANIFEST_PATH = "manifest.json"


def read_json(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def sha256_for_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LauncherApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.config_path = Path(__file__).with_name("config.json")
        self.config = DEFAULT_CONFIG.copy()
        self._load_config()
        self._build_ui()
        self._show_first_run_help()

    def _load_config(self):
        stored = read_json(self.config_path)
        if stored:
            self.config.update(stored)

    def _save_config(self):
        write_json(self.config_path, self.config)

    def _build_ui(self):
        self.master.title(APP_TITLE)
        self.master.geometry("640x520")
        self.master.minsize(640, 520)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        main_frame = ttk.Frame(self, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            main_frame,
            text="Game Launcher",
            font=("Segoe UI", 18, "bold"),
        )
        header.pack(anchor="w")

        ttk.Separator(main_frame).pack(fill="x", pady=10)

        install_frame = ttk.LabelFrame(main_frame, text="Installation")
        install_frame.pack(fill="x", pady=8)

        self.install_var = tk.StringVar(value=self.config.get("install_dir", ""))
        install_entry = ttk.Entry(install_frame, textvariable=self.install_var)
        install_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ttk.Button(install_frame, text="Browse...", command=self._choose_install).pack(
            side="left", padx=8
        )

        exe_frame = ttk.LabelFrame(main_frame, text="Game Executable")
        exe_frame.pack(fill="x", pady=8)
        self.exe_var = tk.StringVar(value=self.config.get("game_exe", ""))
        exe_entry = ttk.Entry(exe_frame, textvariable=self.exe_var)
        exe_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ttk.Button(exe_frame, text="Browse...", command=self._choose_exe).pack(
            side="left", padx=8
        )

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=10)
        ttk.Button(action_frame, text="Save Settings", command=self._save_settings).pack(
            side="left"
        )
        ttk.Button(
            action_frame, text="Download/Update", command=self._start_update
        ).pack(side="left", padx=8)
        self.play_button = ttk.Button(
            action_frame, text="Play", command=self._play_game
        )
        self.play_button.pack(side="right")

        status_frame = ttk.LabelFrame(main_frame, text="Status")
        status_frame.pack(fill="both", expand=True, pady=8)

        self.status_text = tk.Text(
            status_frame,
            height=10,
            wrap="word",
            state="disabled",
            bg="#f9f9f9",
        )
        self.status_text.pack(fill="both", expand=True, padx=8, pady=8)

        self.pack(fill="both", expand=True)
        self._refresh_play_button()

    def _show_first_run_help(self):
        if self.config_path.exists():
            return
        messagebox.showinfo(
            "Quick Setup",
            "Welcome! To get started:\n\n"
            "1) Choose an install folder.\n"
            "2) Choose your game executable.\n"
            "3) Click Download/Update.\n",
        )

    def _choose_install(self):
        folder = filedialog.askdirectory(title="Select game install folder")
        if folder:
            self.install_var.set(folder)

    def _choose_exe(self):
        filename = filedialog.askopenfilename(
            title="Select game executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if filename:
            self.exe_var.set(filename)
            self._refresh_play_button()

    def _save_settings(self):
        self.config.update(
            {
                "install_dir": self.install_var.get().strip(),
                "game_exe": self.exe_var.get().strip(),
            }
        )
        self._save_config()
        self._log("Settings saved.")
        self._refresh_play_button()

    def _refresh_play_button(self):
        exe_path = Path(self.exe_var.get())
        state = "normal" if exe_path.exists() else "disabled"
        self.play_button.config(state=state)

    def _play_game(self):
        exe_path = Path(self.exe_var.get())
        if not exe_path.exists():
            messagebox.showerror("Launch Error", "Game executable not found.")
            return
        os.startfile(exe_path)

    def _start_update(self):
        self._save_settings()
        thread = threading.Thread(target=self._check_updates, daemon=True)
        thread.start()

    def _check_updates(self):
        install_dir = self.config.get("install_dir", "")
        if not install_dir:
            self._log("Please select an install folder before updating.")
            return
        try:
            manifest = self._fetch_manifest()
        except URLError as exc:
            self._log(f"Failed to fetch manifest: {exc}")
            return

        version = manifest.get("version", "unknown")
        files = manifest.get("files", [])
        self._log(f"Remote version: {version}")

        local_version = self._local_version(Path(install_dir))
        if local_version:
            self._log(f"Local version: {local_version}")
        else:
            self._log("Local version: not installed")

        to_download = self._diff_files(Path(install_dir), files)
        if not to_download:
            self._log("No updates needed. You are up to date!")
            return

        self._log(f"Downloading {len(to_download)} file(s)...")
        for item in to_download:
            self._download_file(Path(install_dir), item["path"])
        self._write_version(Path(install_dir), version)
        self._log("Update complete.")

    def _fetch_manifest(self):
        url = (
            f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/"
            f"{REPO_BRANCH}/{MANIFEST_PATH}"
        )
        self._log(f"Fetching manifest: {url}")
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _local_version(self, install_dir):
        version_path = install_dir / "version.txt"
        if not version_path.exists():
            return None
        return version_path.read_text(encoding="utf-8").strip()

    def _write_version(self, install_dir, version):
        install_dir.mkdir(parents=True, exist_ok=True)
        version_path = install_dir / "version.txt"
        version_path.write_text(str(version), encoding="utf-8")

    def _diff_files(self, install_dir, files):
        to_download = []
        for item in files:
            rel_path = Path(item["path"])
            local_path = install_dir / rel_path
            if not local_path.exists():
                to_download.append(item)
                continue
            expected_hash = item.get("sha256")
            if expected_hash:
                actual_hash = sha256_for_file(local_path)
                if actual_hash != expected_hash:
                    to_download.append(item)
        return to_download

    def _download_file(self, install_dir, relative_path):
        url = (
            f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/"
            f"{REPO_BRANCH}/{relative_path}"
        )
        target_path = install_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self._log(f"Downloading {relative_path}")
        with urlopen(url) as response:
            target_path.write_bytes(response.read())

    def _log(self, message):
        def append():
            self.status_text.configure(state="normal")
            self.status_text.insert("end", message + "\n")
            self.status_text.see("end")
            self.status_text.configure(state="disabled")

        self.status_text.after(0, append)

def main():
    root = tk.Tk()
    app = LauncherApp(root)
    app.mainloop()


if __name__ == "__main__":
    main()
