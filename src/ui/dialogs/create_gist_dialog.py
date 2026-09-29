"""Dialog for creating a new GitHub Gist."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from core import GHManager
from ui.widgets import PlaceholderEntry


class CreateGistDialog:
    """Dialog for creating a new code gist."""

    def __init__(
        self,
        parent: tk.Widget,
        gh_manager: GHManager,
        on_created: Optional[Callable[[str], None]] = None,
    ):
        self.parent = parent
        self.gh_manager = gh_manager
        self.on_created = on_created

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("New Gist")
        self.dialog.geometry("540x500")
        self.dialog.minsize(460, 420)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 540
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

        ttk.Label(container, text="Description:").pack(anchor=tk.W, pady=(0, 2))
        self.desc_entry = PlaceholderEntry(container, placeholder="Gist description (optional)")
        self.desc_entry.pack(fill=tk.X, pady=(0, 8))
        self.desc_entry.focus_set()

        row_file = ttk.Frame(container)
        row_file.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(row_file, text="Filename:").pack(side=tk.LEFT, padx=(0, 6))
        self.filename_entry = PlaceholderEntry(row_file, placeholder="e.g., snippet.py", width=25)
        self.filename_entry.set_text("snippet.txt")
        self.filename_entry.pack(side=tk.LEFT, padx=(0, 16))

        self.public_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row_file, text="Make gist public", variable=self.public_var).pack(side=tk.LEFT)

        ttk.Label(container, text="Content:").pack(anchor=tk.W, pady=(0, 2))
        self.content_text = tk.Text(container, height=12, wrap=tk.NONE, font=("Consolas", 9))
        scroll_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.submit_btn = ttk.Button(btn_bar, text="Create Gist", command=self._on_submit, width=14)
        self.submit_btn.pack(side=tk.RIGHT)

    def _on_submit(self) -> None:
        desc = self.desc_entry.get().strip()
        filename = self.filename_entry.get().strip() or "snippet.txt"
        content = self.content_text.get("1.0", tk.END).strip()
        is_public = self.public_var.get()

        if not content:
            messagebox.showwarning("Validation Error", "Gist content cannot be empty.", parent=self.dialog)
            return

        self.submit_btn.config(state=tk.DISABLED, text="Creating...")
        try:
            out = self.gh_manager.gists.create_gist(
                filename=filename,
                content=content,
                description=desc,
                public=is_public,
            )
            messagebox.showinfo("Success", f"Gist created successfully!\n{out}", parent=self.dialog)
            self.dialog.destroy()
            if self.on_created:
                self.on_created(out)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create gist:\n{e}", parent=self.dialog)
            self.submit_btn.config(state=tk.NORMAL, text="Create Gist")
