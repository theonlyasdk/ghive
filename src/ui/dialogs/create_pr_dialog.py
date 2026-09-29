"""Dialog for creating a new GitHub pull request."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from core import GHManager
from ui.widgets import PlaceholderEntry


class CreatePRDialog:
    """Dialog for creating a new pull request in a repository."""

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
        self.dialog.title("New Pull Request")
        self.dialog.geometry("520x500")
        self.dialog.minsize(460, 440)
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
            dh = 500
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

        ttk.Label(container, text="PR Title:").pack(anchor=tk.W, pady=(0, 2))
        self.title_entry = PlaceholderEntry(container, placeholder="Pull request title")
        self.title_entry.pack(fill=tk.X, pady=(0, 8))
        self.title_entry.focus_set()

        branches_row = ttk.Frame(container)
        branches_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(branches_row, text="Base Branch:").pack(side=tk.LEFT)
        self.base_entry = PlaceholderEntry(branches_row, placeholder="main", width=15)
        self.base_entry.set_text("main")
        self.base_entry.pack(side=tk.LEFT, padx=6)

        ttk.Label(branches_row, text="Head Branch:").pack(side=tk.LEFT, padx=(10, 0))
        self.head_entry = PlaceholderEntry(branches_row, placeholder="feature-branch", width=15)
        self.head_entry.pack(side=tk.LEFT, padx=6)

        ttk.Label(container, text="Description:").pack(anchor=tk.W, pady=(0, 2))
        self.body_text = tk.Text(container, height=8, wrap=tk.WORD, font=("Segoe UI", 9))
        self.body_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.draft_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(container, text="Mark as draft", variable=self.draft_var).pack(anchor=tk.W, pady=(0, 12))

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.submit_btn = ttk.Button(btn_bar, text="Create PR", command=self._on_submit, width=14)
        self.submit_btn.pack(side=tk.RIGHT)

    def _on_submit(self) -> None:
        repo = self.repo_entry.get().strip()
        title = self.title_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        base = self.base_entry.get().strip() or None
        head = self.head_entry.get().strip() or None
        draft = self.draft_var.get()

        if not repo:
            messagebox.showwarning("Validation Error", "Repository is required.", parent=self.dialog)
            return

        if not title:
            messagebox.showwarning("Validation Error", "PR title is required.", parent=self.dialog)
            return

        self.submit_btn.config(state=tk.DISABLED, text="Creating...")
        try:
            self.gh_manager.prs.create_pr(
                repo=repo,
                title=title,
                body=body,
                base=base,
                head=head,
                draft=draft,
            )
            messagebox.showinfo("Success", f"Pull request '{title}' created successfully!", parent=self.dialog)
            self.dialog.destroy()
            if self.on_created:
                self.on_created(repo)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create PR:\n{e}", parent=self.dialog)
            self.submit_btn.config(state=tk.NORMAL, text="Create PR")
