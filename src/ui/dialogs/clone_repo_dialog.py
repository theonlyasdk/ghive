"""Dialog for cloning a repository locally."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from core import ConfigManager, GHManager
from ui.widgets import PlaceholderEntry


class CloneRepoDialog:
    """Dialog for cloning a GitHub repository to a local directory."""

    def __init__(
        self,
        parent: tk.Widget,
        gh_manager: GHManager,
        default_repo: str = "",
        on_cloned: Optional[Callable[[str, Path], None]] = None,
    ):
        self.parent = parent
        self.gh_manager = gh_manager
        self.default_repo = default_repo
        self.on_cloned = on_cloned
        self.config = ConfigManager()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Clone Repository")
        self.dialog.geometry("480x280")
        self.dialog.minsize(420, 240)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 480
            dh = 280
            cx = px + (pw // 2) - (dw // 2)
            cy = py + (ph // 2) - (dh // 2)
            self.dialog.geometry(f"{dw}x{dh}+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

        try:
            self.dialog.grab_set()
        except Exception:
            pass
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def _create_widgets(self) -> None:
        container = ttk.Frame(self.dialog, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Repository (owner/repo or URL):").pack(anchor=tk.W, pady=(0, 2))
        self.repo_entry = PlaceholderEntry(container, placeholder="owner/repo or https://github.com/owner/repo")
        self.repo_entry.pack(fill=tk.X, pady=(0, 10))
        if self.default_repo:
            self.repo_entry.set_text(self.default_repo)

        ttk.Label(container, text="Destination Directory:").pack(anchor=tk.W, pady=(0, 2))
        dest_row = ttk.Frame(container)
        dest_row.pack(fill=tk.X, pady=(0, 10))

        default_dest = self.config.get("general", "default_clone_path", str(Path.home() / "Documents" / "GitHub"))
        self.dest_var = tk.StringVar(value=default_dest)
        self.dest_entry = ttk.Entry(dest_row, textvariable=self.dest_var)
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        ttk.Button(dest_row, text="Browse...", command=self._browse_dest).pack(side=tk.RIGHT)

        ttk.Label(container, text="Target Folder Name (Optional):").pack(anchor=tk.W, pady=(0, 2))
        self.folder_entry = PlaceholderEntry(container, placeholder="Optional destination folder name")
        self.folder_entry.pack(fill=tk.X, pady=(0, 16))

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.clone_btn = ttk.Button(btn_bar, text="Clone", command=self._on_clone, width=12)
        self.clone_btn.pack(side=tk.RIGHT)

    def _browse_dest(self) -> None:
        chosen = filedialog.askdirectory(parent=self.dialog)
        if chosen:
            self.dest_var.set(chosen)

    def _on_clone(self) -> None:
        repo = self.repo_entry.get().strip()
        dest = self.dest_var.get().strip()
        folder = self.folder_entry.get().strip() or None

        if not repo:
            messagebox.showwarning("Validation Error", "Repository name or URL is required.", parent=self.dialog)
            return

        if not dest:
            messagebox.showwarning("Validation Error", "Destination directory is required.", parent=self.dialog)
            return

        self.clone_btn.config(state=tk.DISABLED, text="Cloning...")
        try:
            self.gh_manager.repos.clone_repo(repo, dest, folder)
            target_path = Path(dest) / (folder or repo.split("/")[-1].replace(".git", ""))
            messagebox.showinfo("Clone Succeeded", f"Repository cloned successfully to:\n{target_path}", parent=self.dialog)
            self.dialog.destroy()
            if self.on_cloned:
                self.on_cloned(repo, target_path)
        except Exception as e:
            messagebox.showerror("Clone Failed", str(e), parent=self.dialog)
            self.clone_btn.config(state=tk.NORMAL, text="Clone")
