"""Create release dialog for GitHub repositories."""

import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Callable, Optional

from core import GHManager
from ui.widgets import PlaceholderEntry


class CreateReleaseDialog:
    """Dialog for creating a new release with tag, notes, and flags."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        gh_manager: GHManager,
        on_created: Optional[Callable[[str], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.gh_manager = gh_manager
        self.on_created = on_created

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"New Release - {repo}")
        self.dialog.geometry("520x540")
        self.dialog.minsize(460, 480)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 520
            dh = 540
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

        header = ttk.Label(
            container,
            text=f"Create Release for {self.repo}",
            font=("Segoe UI", 12, "bold"),
            foreground="#0969da",
        )
        header.pack(anchor=tk.W, pady=(0, 12))

        # Tag Name
        ttk.Label(container, text="Tag Name (required):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.tag_entry = PlaceholderEntry(container, placeholder="e.g. v1.0.0")
        self.tag_entry.pack(fill=tk.X, pady=(0, 8))

        # Release Title
        ttk.Label(container, text="Release Title:").pack(anchor=tk.W, pady=(0, 2))
        self.title_entry = PlaceholderEntry(container, placeholder="e.g. Initial Release v1.0.0")
        self.title_entry.pack(fill=tk.X, pady=(0, 8))

        # Target branch/commit
        ttk.Label(container, text="Target (branch or commit, optional):").pack(anchor=tk.W, pady=(0, 2))
        self.target_entry = PlaceholderEntry(container, placeholder="e.g. main (defaults to repository default branch)")
        self.target_entry.pack(fill=tk.X, pady=(0, 8))

        # Release Notes
        ttk.Label(container, text="Release Notes:").pack(anchor=tk.W, pady=(0, 2))
        self.notes_text = scrolledtext.ScrolledText(container, height=8, font=("Segoe UI", 9), wrap=tk.WORD)
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Flags (Draft / Pre-release)
        flags_frame = ttk.Frame(container)
        flags_frame.pack(fill=tk.X, pady=(0, 12))

        self.draft_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags_frame, text="Set as a draft release", variable=self.draft_var).pack(anchor=tk.W, pady=2)

        self.prerelease_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags_frame, text="Set as a pre-release", variable=self.prerelease_var).pack(anchor=tk.W, pady=2)

        # Bottom Buttons
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.create_btn = ttk.Button(btn_bar, text="Create Release", command=self._on_create, width=14)
        self.create_btn.pack(side=tk.RIGHT)

    def _on_create(self) -> None:
        tag = self.tag_entry.get().strip()
        if not tag:
            messagebox.showwarning("Validation Error", "Tag name is required.", parent=self.dialog)
            self.tag_entry.focus_set()
            return

        # Validate tag characters
        if re.search(r"[\s~^:?*\[\\]", tag):
            messagebox.showwarning(
                "Invalid Tag Name",
                "Tag name contains invalid characters (spaces, ~, ^, :, ?, *, [, \\ are not allowed).",
                parent=self.dialog,
            )
            self.tag_entry.focus_set()
            return

        title = self.title_entry.get().strip()
        target = self.target_entry.get().strip() or None
        notes = self.notes_text.get("1.0", tk.END).strip()
        draft = self.draft_var.get()
        prerelease = self.prerelease_var.get()

        self.create_btn.config(state=tk.DISABLED, text="Creating...")

        def _do_create():
            try:
                self.gh_manager.releases.create_release(
                    repo=self.repo,
                    tag=tag,
                    title=title,
                    notes=notes,
                    draft=draft,
                    prerelease=prerelease,
                    target=target,
                )
                self.dialog.after(0, lambda t=tag: self._on_success(t))
            except Exception as exc:
                err_msg = str(exc)
                self.dialog.after(0, lambda err=err_msg: self._on_error(err))

        import threading
        threading.Thread(target=_do_create, daemon=True).start()

    def _on_success(self, tag: str) -> None:
        self.dialog.destroy()
        messagebox.showinfo("Release Created", f"Successfully created release '{tag}'!", parent=self.parent)
        if self.on_created:
            self.on_created(tag)

    def _on_error(self, exc: Exception) -> None:
        self.create_btn.config(state=tk.NORMAL, text="Create Release")
        messagebox.showerror("Error", f"Failed to create release:\n{exc}", parent=self.dialog)
