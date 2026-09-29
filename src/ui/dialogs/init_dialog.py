"""Dependency check and initialization dialog."""

import platform
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Tuple

from core import ConfigManager, DependencyManager


class InitDialog:
    """Dialog displayed when GitHub CLI dependency is missing on startup."""

    def __init__(self, parent: Optional[tk.Widget] = None):
        self.dialog = tk.Toplevel(parent) if parent else tk.Tk()
        self.dialog.title("ghive - Dependency Check")
        self.dialog.geometry("520x420")
        self.dialog.minsize(480, 380)

        self.dep_manager = DependencyManager()
        self.config = ConfigManager()

        self.gh_path: Optional[Path] = None
        self.success = False

        self._create_widgets()
        self._check()

        # Center dialog
        self.dialog.update_idletasks()
        try:
            sw = self.dialog.winfo_screenwidth()
            sh = self.dialog.winfo_screenheight()
            dw = 520
            dh = 420
            cx = (sw // 2) - (dw // 2)
            cy = (sh // 2) - (dh // 2)
            self.dialog.geometry(f"{dw}x{dh}+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

    def _create_widgets(self) -> None:
        container = ttk.Frame(self.dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(
            container,
            text="GitHub CLI Required",
            font=("Segoe UI", 14, "bold"),
            fg="#24292f",
        )
        title.pack(pady=(0, 8))

        desc = tk.Label(
            container,
            text="ghive is a native graphical frontend for GitHub CLI ('gh').\nPlease ensure GitHub CLI is installed.",
            font=("Segoe UI", 9),
            justify=tk.CENTER,
            fg="#57606a",
        )
        desc.pack(pady=(0, 16))

        box = ttk.LabelFrame(container, text="Dependency Status", padding=12)
        box.pack(fill=tk.X, pady=(0, 12))

        self.status_label = tk.Label(
            box,
            text="Searching for GitHub CLI...",
            font=("Segoe UI", 10),
            anchor=tk.W,
        )
        self.status_label.pack(fill=tk.X, pady=(0, 4))

        self.path_label = tk.Label(
            box,
            text="",
            font=("Consolas", 8),
            fg="#57606a",
            anchor=tk.W,
        )
        self.path_label.pack(fill=tk.X)

        guide = self.dep_manager.get_install_guide().get(
            self.dep_manager.system,
            ("https://github.com/cli/cli/releases/latest", "sudo apt install gh"),
        )
        self.download_url, self.install_cmd = guide

        install_box = ttk.LabelFrame(container, text="Installation Options", padding=12)
        install_box.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        lbl_cmd = tk.Label(
            install_box,
            text=f"Install via terminal: {self.install_cmd}",
            font=("Consolas", 9),
            anchor=tk.W,
            fg="#0969da",
        )
        lbl_cmd.pack(fill=tk.X, pady=(0, 8))

        action_row = ttk.Frame(install_box)
        action_row.pack(fill=tk.X)

        ttk.Button(action_row, text="Open Download Page", command=self._open_download_url).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(action_row, text="Locate gh Manually...", command=self._browse_custom_path).pack(side=tk.LEFT)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.continue_btn = ttk.Button(
            btn_bar,
            text="Continue",
            command=self._on_continue,
            state=tk.DISABLED,
            width=12,
        )
        self.continue_btn.pack(side=tk.RIGHT, padx=(6, 0))

        ttk.Button(
            btn_bar,
            text="Recheck",
            command=self._check,
            width=10,
        ).pack(side=tk.RIGHT, padx=6)

        ttk.Button(
            btn_bar,
            text="Exit",
            command=self.dialog.destroy,
            width=10,
        ).pack(side=tk.RIGHT)

    def _check(self) -> None:
        try:
            path = self.dep_manager.get_gh_path()
            ver = self.dep_manager.get_gh_version(path)
            self.gh_path = path
            self.status_label.config(text=f"✓ GitHub CLI Found ({ver})", fg="#1a7f37")
            self.path_label.config(text=str(path))
            self.continue_btn.config(state=tk.NORMAL)
            self.success = True
        except Exception:
            self.status_label.config(text="✗ GitHub CLI not found on this system", fg="#cf222e")
            self.path_label.config(text="Please install gh or specify path manually.")
            self.continue_btn.config(state=tk.DISABLED)
            self.success = False

    def _open_download_url(self) -> None:
        webbrowser.open(self.download_url)

    def _browse_custom_path(self) -> None:
        file_types = [("Executable", "*.exe")] if self.dep_manager.system == "windows" else [("All Files", "*")]
        chosen = filedialog.askopenfilename(title="Select gh Executable", filetypes=file_types, parent=self.dialog)
        if chosen and Path(chosen).is_file():
            self.config.set("paths", "gh", chosen)
            self._check()

    def _on_continue(self) -> None:
        self.success = True
        self.dialog.destroy()

    def run(self) -> Tuple[bool, Optional[Path]]:
        """Run the dialog and return (success, gh_path)."""
        self.dialog.mainloop()
        return self.success, self.gh_path
