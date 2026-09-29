"""Preferences dialog for ghive settings."""

import shutil
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from core import ConfigManager, DependencyManager


class PreferencesDialog:
    """Dialog allowing user to customize ghive configuration."""

    def __init__(self, parent: tk.Widget, on_preferences_changed: Optional[Callable[[], None]] = None):
        self.parent = parent
        self.on_preferences_changed = on_preferences_changed
        self.config = ConfigManager()
        self.dep_manager = DependencyManager()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Preferences")
        self.dialog.geometry("580x460")
        self.dialog.minsize(520, 420)
        self.dialog.transient(parent)

        self._create_widgets()
        self._load_settings()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 580
            dh = 460
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
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        general_tab = self._create_general_tab(notebook)
        tools_tab = self._create_tools_tab(notebook)
        confirm_tab = self._create_confirm_tab(notebook)

        notebook.add(general_tab, text="General")
        notebook.add(tools_tab, text="External Tools")
        notebook.add(confirm_tab, text="Confirmations")

        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=12).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="OK", command=self._on_ok, width=12).pack(side=tk.RIGHT)

    def _create_general_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook, padding=12)

        gen_frame = ttk.LabelFrame(tab, text="Fetch & Display", padding=10)
        gen_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(gen_frame, text="Default items per page:").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.limit_var = tk.StringVar(value="30")
        limit_cb = ttk.Combobox(
            gen_frame,
            textvariable=self.limit_var,
            values=["15", "30", "50", "100"],
            state="readonly",
            width=10,
        )
        limit_cb.grid(row=0, column=1, sticky=tk.W, padx=10, pady=6)

        clone_frame = ttk.LabelFrame(tab, text="Default Clone Location", padding=10)
        clone_frame.pack(fill=tk.X, pady=(0, 10))

        self.clone_path_var = tk.StringVar()
        clone_entry = ttk.Entry(clone_frame, textvariable=self.clone_path_var)
        clone_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ttk.Button(clone_frame, text="Browse...", command=self._browse_clone_dir).pack(side=tk.RIGHT)

        return tab

    def _create_tools_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook, padding=12)

        gh_frame = ttk.LabelFrame(tab, text="GitHub CLI (gh) Path", padding=10)
        gh_frame.pack(fill=tk.X, pady=(0, 10))

        self.gh_path_var = tk.StringVar()
        gh_entry = ttk.Entry(gh_frame, textvariable=self.gh_path_var)
        gh_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(gh_frame, text="Download", command=self._download_gh).pack(side=tk.LEFT, padx=2)
        ttk.Button(gh_frame, text="Auto-Detect", command=self._autodetect_gh).pack(side=tk.LEFT, padx=2)
        ttk.Button(gh_frame, text="Browse...", command=self._browse_gh).pack(side=tk.LEFT, padx=2)

        self.gh_version_label = ttk.Label(tab, text="Version: Detecting...", foreground="#57606a")
        self.gh_version_label.pack(anchor=tk.W, padx=4, pady=(0, 10))

        git_frame = ttk.LabelFrame(tab, text="Git Path (Optional)", padding=10)
        git_frame.pack(fill=tk.X, pady=(0, 10))

        self.git_path_var = tk.StringVar()
        git_entry = ttk.Entry(git_frame, textvariable=self.git_path_var)
        git_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(git_frame, text="Download", command=self._download_git).pack(side=tk.LEFT, padx=2)
        ttk.Button(git_frame, text="Auto-Detect", command=self._autodetect_git).pack(side=tk.LEFT, padx=2)
        ttk.Button(git_frame, text="Browse...", command=self._browse_git).pack(side=tk.LEFT, padx=2)

        return tab

    def _create_confirm_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook, padding=12)

        confirm_frame = ttk.LabelFrame(tab, text="Prompt Confirmation Before Destructive Actions", padding=10)
        confirm_frame.pack(fill=tk.X)

        self.confirm_delete_repo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            confirm_frame,
            text="Confirm before deleting a repository",
            variable=self.confirm_delete_repo_var,
        ).pack(anchor=tk.W, pady=4)

        self.confirm_delete_gist_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            confirm_frame,
            text="Confirm before deleting a gist",
            variable=self.confirm_delete_gist_var,
        ).pack(anchor=tk.W, pady=4)

        self.confirm_close_issue_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            confirm_frame,
            text="Confirm before closing an issue",
            variable=self.confirm_close_issue_var,
        ).pack(anchor=tk.W, pady=4)

        self.confirm_close_pr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            confirm_frame,
            text="Confirm before closing a pull request",
            variable=self.confirm_close_pr_var,
        ).pack(anchor=tk.W, pady=4)

        self.confirm_merge_pr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            confirm_frame,
            text="Confirm before merging a pull request",
            variable=self.confirm_merge_pr_var,
        ).pack(anchor=tk.W, pady=4)

        return tab

    def _load_settings(self) -> None:
        self.limit_var.set(str(self.config.get("general", "default_limit", 30)))
        self.clone_path_var.set(self.config.get("general", "default_clone_path", ""))

        gh_path = self.config.get("paths", "gh", "")
        if not gh_path:
            try:
                gh_path = str(self.dep_manager.get_gh_path())
            except Exception:
                gh_path = ""
        self.gh_path_var.set(gh_path)

        git_path = self.config.get("paths", "git", "")
        if not git_path:
            detected_git = self.dep_manager.get_git_path()
            git_path = str(detected_git) if detected_git else ""
        self.git_path_var.set(git_path)

        self.confirm_delete_repo_var.set(self.config.get("confirmations", "confirm_delete_repo", True))
        self.confirm_delete_gist_var.set(self.config.get("confirmations", "confirm_delete_gist", True))
        self.confirm_close_issue_var.set(self.config.get("confirmations", "confirm_close_issue", True))
        self.confirm_close_pr_var.set(self.config.get("confirmations", "confirm_close_pr", True))
        self.confirm_merge_pr_var.set(self.config.get("confirmations", "confirm_merge_pr", True))

        self._update_gh_version_display()

    def _update_gh_version_display(self) -> None:
        path = self.gh_path_var.get()
        if path and Path(path).is_file():
            ver = self.dep_manager.get_gh_version(Path(path))
            self.gh_version_label.config(text=f"Version: {ver}", foreground="#1a7f37")
        else:
            self.gh_version_label.config(text="Version: Not found", foreground="#cf222e")

    def _download_gh(self) -> None:
        webbrowser.open("https://cli.github.com/")

    def _download_git(self) -> None:
        webbrowser.open("https://git-scm.com/downloads")

    def _autodetect_gh(self) -> None:
        try:
            detected = self.dep_manager.get_gh_path()
            self.gh_path_var.set(str(detected))
            self._update_gh_version_display()
        except Exception as e:
            if messagebox.askyesno(
                "GitHub CLI Not Found",
                f"Could not auto-detect GitHub CLI:\n{e}\n\nDo you want to open the official download page?",
                parent=self.dialog,
            ):
                self._download_gh()

    def _autodetect_git(self) -> None:
        detected = self.dep_manager.get_git_path()
        if detected:
            self.git_path_var.set(str(detected))
        else:
            if messagebox.askyesno(
                "Git Not Found",
                "Git executable was not found on PATH.\n\nDo you want to open the official download page?",
                parent=self.dialog,
            ):
                self._download_git()

    def _browse_gh(self) -> None:
        file_types = [("Executable", "*.exe")] if self.dep_manager.system == "windows" else [("All Files", "*")]
        chosen = filedialog.askopenfilename(title="Select gh Executable", filetypes=file_types, parent=self.dialog)
        if chosen:
            self.gh_path_var.set(chosen)
            self._update_gh_version_display()

    def _browse_git(self) -> None:
        file_types = [("Executable", "*.exe")] if self.dep_manager.system == "windows" else [("All Files", "*")]
        chosen = filedialog.askopenfilename(title="Select git Executable", filetypes=file_types, parent=self.dialog)
        if chosen:
            self.git_path_var.set(chosen)

    def _browse_clone_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Select Default Clone Directory", parent=self.dialog)
        if chosen:
            self.clone_path_var.set(chosen)

    def _on_ok(self) -> None:
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 30

        self.config.set("general", "default_limit", limit)
        self.config.set("general", "default_clone_path", self.clone_path_var.get().strip())
        self.config.set("paths", "gh", self.gh_path_var.get().strip())
        self.config.set("paths", "git", self.git_path_var.get().strip())

        self.config.set("confirmations", "confirm_delete_repo", self.confirm_delete_repo_var.get())
        self.config.set("confirmations", "confirm_delete_gist", self.confirm_delete_gist_var.get())
        self.config.set("confirmations", "confirm_close_issue", self.confirm_close_issue_var.get())
        self.config.set("confirmations", "confirm_close_pr", self.confirm_close_pr_var.get())
        self.config.set("confirmations", "confirm_merge_pr", self.confirm_merge_pr_var.get())

        self.dialog.destroy()
        if self.on_preferences_changed:
            self.on_preferences_changed()

    def show(self) -> None:
        """Wait for the preferences dialog to close."""
        self.dialog.wait_window()
