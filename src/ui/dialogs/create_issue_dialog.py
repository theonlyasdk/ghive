"""Dialog for creating a new GitHub issue."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from core import GHManager
from ui.widgets import PlaceholderEntry


class CreateIssueDialog:
    """Dialog for creating a new issue in a repository."""

    def __init__(
        self,
        parent: tk.Widget,
        default_repo: str,
        gh_manager: GHManager,
        on_created: Optional[Callable[[str], None]] = None,
    ):
        self.parent = parent
        self.default_repo = default_repo
        self.gh_manager = gh_manager
        self.on_created = on_created

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("New Issue")
        self.dialog.geometry("552x480")
        self.dialog.minsize(492, 420)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 552
            dh = 480
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

        ttk.Label(container, text="Repository:").pack(anchor=tk.W, pady=(0, 2))
        self.repo_entry = PlaceholderEntry(container, placeholder="owner/repo")
        self.repo_entry.pack(fill=tk.X, pady=(0, 8))
        if self.default_repo:
            self.repo_entry.set_text(self.default_repo)

        ttk.Label(container, text="Issue Title:").pack(anchor=tk.W, pady=(0, 2))
        self.title_entry = PlaceholderEntry(container, placeholder="Title of the issue")
        self.title_entry.pack(fill=tk.X, pady=(0, 8))
        self.title_entry.focus_set()

        ttk.Label(container, text="Description:").pack(anchor=tk.W, pady=(0, 2))
        self.body_text = tk.Text(container, height=8, wrap=tk.WORD, font=("Segoe UI", 9))
        self.body_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        row_meta = ttk.Frame(container)
        row_meta.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(row_meta, text="Labels (comma-sep):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.labels_entry = PlaceholderEntry(row_meta, placeholder="bug, enhancement...", width=22)
        self.labels_entry.grid(row=0, column=1, sticky=tk.W, padx=6, pady=2)

        ttk.Label(row_meta, text="Assignees:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.assignees_entry = PlaceholderEntry(row_meta, placeholder="username...", width=20)
        self.assignees_entry.grid(row=0, column=3, sticky=tk.W, padx=6, pady=2)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.submit_btn = ttk.Button(btn_bar, text="Submit Issue", command=self._on_submit, width=14)
        self.submit_btn.pack(side=tk.RIGHT)

    def _on_submit(self) -> None:
        repo = self.repo_entry.get().strip()
        title = self.title_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()

        if not repo:
            messagebox.showwarning("Validation Error", "Repository is required.", parent=self.dialog)
            return

        if not title:
            messagebox.showwarning("Validation Error", "Issue title is required.", parent=self.dialog)
            return

        labels_raw = self.labels_entry.get().strip()
        labels = [l.strip() for l in labels_raw.split(",") if l.strip()] if labels_raw else None

        assignees_raw = self.assignees_entry.get().strip()
        assignees = [a.strip() for a in assignees_raw.split(",") if a.strip()] if assignees_raw else None

        self.submit_btn.config(state=tk.DISABLED, text="Submitting...")
        try:
            self.gh_manager.issues.create_issue(
                repo=repo,
                title=title,
                body=body,
                labels=labels,
                assignees=assignees,
            )
            messagebox.showinfo("Success", f"Issue '{title}' created successfully!", parent=self.dialog)
            self.dialog.destroy()
            if self.on_created:
                self.on_created(repo)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create issue:\n{e}", parent=self.dialog)
            self.submit_btn.config(state=tk.NORMAL, text="Submit Issue")
