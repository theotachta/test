import hashlib
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.error import URLError
from urllib.request import Request, urlopen

APP_TITLE = "Game Launcher"
DEFAULT_CONFIG = {
    "install_dir": "",
    "game_exe": "",
}
REPO_OWNER = "theotachta"
REPO_NAME = "test"
REPO_BRANCH = "codex/create-simple-auto-patcher-for-game"
MANIFEST_PATH = "manifest.json"
ASSETS_DIR = Path(__file__).with_name("assets")
WALLPAPER_PATH = ASSETS_DIR / "wallpaper.png"
LOGO_PATH = ASSETS_DIR / "logo.png"


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
        self.remote_version = None
        self.update_required = False
        self._load_config()
        self._build_ui()
        self._show_first_run_help()
        self._start_startup_check()

    def _load_config(self):
        stored = read_json(self.config_path)
        if stored:
            self.config.update(stored)

    def _save_config(self):
        write_json(self.config_path, self.config)

    def _build_ui(self):
        self.master.title(APP_TITLE)
        self.master.geometry("1180x720")
        self.master.minsize(980, 640)
        self.master.configure(bg="#121317")
        self.master.overrideredirect(True)
        self._center_window(1180, 720)
        self.master.bind("<Map>", self._on_map_restore)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), foreground="#ffffff")
        style.configure("Subtle.TLabel", font=("Segoe UI", 10), foreground="#a7abb8")
        style.configure("Nav.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 12, "bold"))
        style.configure("Secondary.TButton", font=("Segoe UI", 10))

        outer = tk.Frame(self, bg="#121317")
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_title_bar(outer)
        body = tk.Frame(outer, bg="#121317")
        body.pack(fill=tk.BOTH, expand=True)

        self._build_sidebar(body)
        self._build_pages(body)

        self.pack(fill="both", expand=True)
        self._refresh_main_action_button()
        self.update_button_state()

    def _build_title_bar(self, parent):
        title_bar = tk.Frame(parent, bg="#171922", height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        logo = self._load_logo(title_bar)
        if logo is not None:
            logo_label = tk.Label(title_bar, image=logo, bg="#171922")
            logo_label.image = logo
            logo_label.pack(side="left", padx=(14, 8))

        title = tk.Label(
            title_bar,
            text=APP_TITLE,
            bg="#171922",
            fg="#ffffff",
            font=("Segoe UI", 12, "bold"),
        )
        title.pack(side="left")

        title_bar.bind("<ButtonPress-1>", self._start_move)
        title_bar.bind("<B1-Motion>", self._do_move)
        title.bind("<ButtonPress-1>", self._start_move)
        title.bind("<B1-Motion>", self._do_move)

        control_frame = tk.Frame(title_bar, bg="#171922")
        control_frame.pack(side="right", padx=8)

        ttk.Button(
            control_frame,
            text="—",
            width=3,
            command=self._minimize_window,
            style="Secondary.TButton",
        ).pack(side="left", padx=4)
        ttk.Button(
            control_frame,
            text="✕",
            width=3,
            command=self.master.destroy,
            style="Secondary.TButton",
        ).pack(side="left")

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg="#1b1d28", width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        nav_title = tk.Label(
            sidebar,
            text="MENU",
            bg="#1b1d28",
            fg="#a7abb8",
            font=("Segoe UI", 9, "bold"),
        )
        nav_title.pack(anchor="w", padx=16, pady=(20, 8))

        self.nav_buttons = {}
        for name in ("Game", "News", "Profile"):
            button = ttk.Button(
                sidebar,
                text=name,
                command=lambda page=name: self._show_page(page),
                style="Nav.TButton",
            )
            button.pack(fill="x", padx=12, pady=6)
            self.nav_buttons[name] = button

    def _build_pages(self, parent):
        self.page_container = tk.Frame(parent, bg="#121317")
        self.page_container.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self.pages["Game"] = self._build_game_page(self.page_container)
        self.pages["News"] = self._build_news_page(self.page_container)
        self.pages["Profile"] = self._build_profile_page(self.page_container)

        self._show_page("Game")

    def _build_game_page(self, parent):
        page = tk.Frame(parent, bg="#121317")
        page.pack(fill="both", expand=True)

        hero = tk.Canvas(page, bg="#121317", highlightthickness=0)
        hero.pack(fill="both", expand=True, padx=20, pady=20)

        self.wallpaper_original = self._load_wallpaper()
        self.wallpaper_image = None
        if self.wallpaper_original is not None:
            self.wallpaper_image = self.wallpaper_original
            self.wallpaper_canvas_id = hero.create_image(
                0, 0, anchor="nw", image=self.wallpaper_image
            )
            hero.bind("<Configure>", self._update_wallpaper)

        hero.create_rectangle(
            0, 0, 1400, 120,
            fill="#121317",
            stipple="gray50",
            outline="",
        )
        hero.create_text(
            28,
            28,
            anchor="nw",
            text="Your Game",
            fill="#ffffff",
            font=("Segoe UI", 24, "bold"),
        )
        hero.create_text(
            28,
            68,
            anchor="nw",
            text="Latest updates and quick launch",
            fill="#a7abb8",
            font=("Segoe UI", 11),
        )

        control_panel = tk.Frame(page, bg="#171922")
        control_panel.place(relx=0.02, rely=0.62, relwidth=0.96, relheight=0.32)

        left_panel = tk.Frame(control_panel, bg="#171922")
        left_panel.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        install_label = tk.Label(
            left_panel, text="Installation", bg="#171922", fg="#a7abb8"
        )
        install_label.pack(anchor="w")

        self.install_var = tk.StringVar(value=self.config.get("install_dir", ""))
        install_entry = ttk.Entry(left_panel, textvariable=self.install_var)
        install_entry.pack(fill="x", pady=(6, 10))
        ttk.Button(
            left_panel, text="Browse...", command=self._choose_install, style="Secondary.TButton"
        ).pack(anchor="w")

        exe_label = tk.Label(
            left_panel, text="Game Executable", bg="#171922", fg="#a7abb8"
        )
        exe_label.pack(anchor="w", pady=(16, 0))

        self.exe_var = tk.StringVar(value=self.config.get("game_exe", ""))
        exe_entry = ttk.Entry(left_panel, textvariable=self.exe_var)
        exe_entry.pack(fill="x", pady=(6, 10))
        ttk.Button(
            left_panel, text="Browse...", command=self._choose_exe, style="Secondary.TButton"
        ).pack(anchor="w")

        right_panel = tk.Frame(control_panel, bg="#171922")
        right_panel.pack(side="right", fill="y", padx=16, pady=16)

        ttk.Button(
            right_panel,
            text="Validate Data",
            command=self._start_validate,
            style="Secondary.TButton",
        ).pack(fill="x", pady=(0, 12))

        self.main_action_button = ttk.Button(
            right_panel,
            text="Update",
            command=self._handle_main_action,
            style="Primary.TButton",
        )
        self.main_action_button.pack(fill="x")

        status_frame = tk.Frame(page, bg="#121317")
        status_frame.place(relx=0.02, rely=0.86, relwidth=0.96, relheight=0.12)

        status_title = tk.Label(
            status_frame,
            text="Status",
            bg="#121317",
            fg="#a7abb8",
            font=("Segoe UI", 10, "bold"),
        )
        status_title.pack(anchor="w")

        self.status_text = tk.Text(
            status_frame,
            height=6,
            wrap="word",
            state="disabled",
            bg="#1b1d28",
            fg="#e5e7ef",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.status_text.pack(fill="both", expand=True, pady=(6, 0))

        return page

    def _build_news_page(self, parent):
        page = tk.Frame(parent, bg="#121317")
        page.pack(fill="both", expand=True)
        label = tk.Label(
            page,
            text="News",
            bg="#121317",
            fg="#ffffff",
            font=("Segoe UI", 18, "bold"),
        )
        label.pack(anchor="nw", padx=24, pady=24)
        sub = tk.Label(
            page,
            text="No news yet.",
            bg="#121317",
            fg="#a7abb8",
            font=("Segoe UI", 11),
        )
        sub.pack(anchor="nw", padx=24)
        return page

    def _build_profile_page(self, parent):
        page = tk.Frame(parent, bg="#121317")
        page.pack(fill="both", expand=True)
        label = tk.Label(
            page,
            text="Profile",
            bg="#121317",
            fg="#ffffff",
            font=("Segoe UI", 18, "bold"),
        )
        label.pack(anchor="nw", padx=24, pady=24)
        sub = tk.Label(
            page,
            text="Profile setup coming soon.",
            bg="#121317",
            fg="#a7abb8",
            font=("Segoe UI", 11),
        )
        sub.pack(anchor="nw", padx=24)
        return page

    def _show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for key, button in self.nav_buttons.items():
            button.state(["!pressed"])
            button.configure(style="Nav.TButton")
            if key == name:
                button.configure(style="Primary.TButton")

    def _load_wallpaper(self):
        if not WALLPAPER_PATH.exists():
            return None
        try:
            return tk.PhotoImage(file=str(WALLPAPER_PATH))
        except tk.TclError:
            return None

    def _load_logo(self, parent):
        if not LOGO_PATH.exists():
            return None
        try:
            return tk.PhotoImage(file=str(LOGO_PATH))
        except tk.TclError:
            return None

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        x = self.master.winfo_pointerx() - self._drag_x
        y = self.master.winfo_pointery() - self._drag_y
        self.master.geometry(f"+{x}+{y}")

    def _center_window(self, width, height):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        self.master.geometry(f"{width}x{height}+{x}+{y}")

    def _minimize_window(self):
        self.master.overrideredirect(False)
        self.master.iconify()

    def _on_map_restore(self, event):
        self.master.after(0, lambda: self.master.overrideredirect(True))

    def _update_wallpaper(self, event):
        if self.wallpaper_original is None:
            return
        canvas = event.widget
        canvas_width = max(canvas.winfo_width(), 1)
        canvas_height = max(canvas.winfo_height(), 1)
        self.wallpaper_image = self._scale_image_to_fit(
            self.wallpaper_original, canvas_width, canvas_height
        )
        canvas.itemconfig(self.wallpaper_canvas_id, image=self.wallpaper_image)

    def _scale_image_to_fit(self, image, target_width, target_height):
        img_width = image.width()
        img_height = image.height()
        if img_width == 0 or img_height == 0:
            return image
        scale = min(target_width / img_width, target_height / img_height)
        if scale == 1:
            return image
        if scale > 1:
            factor = max(int(scale * 100), 1)
            return image.zoom(factor, factor).subsample(100, 100)
        factor = max(int((1 / scale) * 100), 1)
        return image.zoom(100, 100).subsample(factor, factor)

    def _show_first_run_help(self):
        if self.config_path.exists():
            return
        messagebox.showinfo(
            "Quick Setup",
            "Welcome! To get started:\n\n"
            "1) Choose an install folder.\n"
            "2) Choose your game executable.\n"
            "3) Click Validate Data, then Update if needed.\n",
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
            self._refresh_main_action_button()

    def _save_settings(self):
        self.config.update(
            {
                "install_dir": self.install_var.get().strip(),
                "game_exe": self.exe_var.get().strip(),
            }
        )
        self._save_config()
        self._log("Settings saved.")
        self._refresh_main_action_button()

    def _refresh_main_action_button(self):
        exe_path = Path(self.exe_var.get())
        state = "normal" if exe_path.exists() else "disabled"
        if not self.update_required:
            self.main_action_button.config(state=state)

    def _play_game(self):
        exe_path = Path(self.exe_var.get())
        if not exe_path.exists():
            messagebox.showerror("Launch Error", "Game executable not found.")
            return
        os.startfile(exe_path)

    def _handle_main_action(self):
        if self.update_required:
            self._start_update()
        else:
            self._play_game()

    def _start_update(self):
        self._save_settings()
        thread = threading.Thread(target=lambda: self._check_updates(download=True), daemon=True)
        thread.start()

    def _start_validate(self):
        self._save_settings()
        thread = threading.Thread(target=lambda: self._check_updates(download=False), daemon=True)
        thread.start()

    def _start_startup_check(self):
        thread = threading.Thread(target=lambda: self._check_updates(download=False), daemon=True)
        thread.start()

    def _check_updates(self, download):
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
        self.remote_version = str(version)
        self._log(f"Remote version: {version}")

        local_version = self._local_version(Path(install_dir))
        if local_version:
            self._log(f"Local version: {local_version}")
        else:
            self._log("Local version: not installed")

        to_download = self._diff_files(Path(install_dir), files, version)
        if not to_download:
            self.update_required = False
            self.update_button_state()
            self._log("No updates needed. You are good to go!")
            return

        self.update_required = True
        self.update_button_state()
        total_bytes = self._calculate_download_size(to_download)
        if total_bytes is None:
            self._log(f"Update available: {len(to_download)} file(s).")
        else:
            self._log(
                f"Update available: {len(to_download)} file(s) "
                f"({self._format_bytes(total_bytes)})."
            )

        if not download:
            return

        self._log("Downloading updates...")
        for item in to_download:
            self._download_file(Path(install_dir), item["path"])
        self._write_version(Path(install_dir), version)
        self.update_required = False
        self.update_button_state()
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

    def _diff_files(self, install_dir, files, remote_version):
        to_download = []
        for item in files:
            if item.get("skip") is True:
                continue
            rel_path = Path(item["path"])
            local_path = install_dir / rel_path
            if not local_path.exists():
                to_download.append(item)
                continue
            if rel_path.name == "version.txt":
                if self._local_version(install_dir) == str(remote_version):
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

    def update_button_state(self):
        def apply_state():
            if self.update_required:
                self.main_action_button.config(text="Update", state="normal")
            else:
                self.main_action_button.config(text="Play")
                self._refresh_main_action_button()

        self.status_text.after(0, apply_state)

    def _calculate_download_size(self, items):
        total = 0
        for item in items:
            size = item.get("size")
            if isinstance(size, int):
                total += size
                continue
            size = self._fetch_remote_size(item["path"])
            if size is None:
                return None
            total += size
        return total

    def _fetch_remote_size(self, relative_path):
        url = (
            f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/"
            f"{REPO_BRANCH}/{relative_path}"
        )
        request = Request(url, method="HEAD")
        response = urlopen(request)
        try:
            length = response.headers.get("Content-Length")
        finally:
            response.close()
        if length is None:
            return None
        try:
            return int(length)
        except ValueError:
            return None

    @staticmethod
    def _format_bytes(size):
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024

def main():
    root = tk.Tk()
    app = LauncherApp(root)
    app.mainloop()


if __name__ == "__main__":
    main()
