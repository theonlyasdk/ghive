"""Dialog for creating a new GitHub repository."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from core import ConfigManager, GHManager
from ui.widgets import PlaceholderEntry


class CreateRepoDialog:
    """Dialog for creating a new repository with customization options."""

    def __init__(self, parent: tk.Widget, gh_manager: GHManager, on_created: Optional[Callable[[str], None]] = None):
        self.parent = parent
        self.gh_manager = gh_manager
        self.on_created = on_created
        self.config = ConfigManager()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("New Repository")
        self.dialog.geometry("480x530")
        self.dialog.minsize(440, 490)
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
            dh = 530
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

        form = ttk.Frame(container)
        form.pack(fill=tk.BOTH, expand=True)

        ttk.Label(form, text="Repository Name:").pack(anchor=tk.W, pady=(0, 2))
        self.name_entry = PlaceholderEntry(form, placeholder="e.g., my-awesome-project")
        self.name_entry.pack(fill=tk.X, pady=(0, 10))
        self.name_entry.focus_set()

        ttk.Label(form, text="Description:").pack(anchor=tk.W, pady=(0, 2))
        self.desc_entry = PlaceholderEntry(form, placeholder="Short description of your project (optional)")
        self.desc_entry.pack(fill=tk.X, pady=(0, 10))

        vis_frame = ttk.LabelFrame(form, text="Visibility", padding=8)
        vis_frame.pack(fill=tk.X, pady=(0, 10))

        self.vis_var = tk.StringVar(value="public")
        ttk.Radiobutton(vis_frame, text="Public (Anyone can see this repository)", variable=self.vis_var, value="public").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(vis_frame, text="Private (You choose who can see this repository)", variable=self.vis_var, value="private").pack(anchor=tk.W, pady=2)

        init_frame = ttk.LabelFrame(form, text="Initialization", padding=8)
        init_frame.pack(fill=tk.X, pady=(0, 10))

        self.readme_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(init_frame, text="Add a README file", variable=self.readme_var).pack(anchor=tk.W, pady=2)

        row_extra = ttk.Frame(init_frame)
        row_extra.pack(fill=tk.X, pady=4)

        ttk.Label(row_extra, text=".gitignore:").pack(side=tk.LEFT)
        self.gitignore_var = tk.StringVar(value="None")
        gitignore_cb = ttk.Combobox(
            row_extra,
            textvariable=self.gitignore_var,
            values=["None", "Python", "Node", "Go", "Rust", "Java", "C++"],
            state="readonly",
            width=10,
        )
        gitignore_cb.pack(side=tk.LEFT, padx=6)

        ttk.Label(row_extra, text="License:").pack(side=tk.LEFT, padx=(6, 0))
        self.license_var = tk.StringVar(value="mit")
        license_cb = ttk.Combobox(
            row_extra,
            textvariable=self.license_var,
            values=["mit", "apache-2.0", "gpl-3.0", "bsd-3-clause", "None"],
            state="readonly",
            width=12,
        )
        license_cb.pack(side=tk.LEFT, padx=6)

        clone_frame = ttk.LabelFrame(form, text="Clone Options...", padding=8)
        clone_frame.pack(fill=tk.X, pady=(0, 10))

        self.clone_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(clone_frame, text="Clone repository locally after creation", variable=self.clone_var, command=self._toggle_clone).pack(anchor=tk.W, pady=2)

        self.clone_path_frame = ttk.Frame(clone_frame)
        self.clone_path_var = tk.StringVar(value=self.config.get("general", "default_clone_path", ""))
        self.clone_entry = ttk.Entry(self.clone_path_frame, textvariable=self.clone_path_var)
        self.clone_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(self.clone_path_frame, text="Browse...", command=self._browse_dir).pack(side=tk.RIGHT)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        self.submit_btn = ttk.Button(btn_bar, text="Create", command=self._on_submit, width=12)
        self.submit_btn.pack(side=tk.RIGHT)

    def _toggle_clone(self) -> None:
        if self.clone_var.get():
            self.clone_path_frame.pack(fill=tk.X, pady=4)
        else:
            self.clone_path_frame.pack_forget()

    def _browse_dir(self) -> None:
        chosen = filedialog.askdirectory(parent=self.dialog)
        if chosen:
            self.clone_path_var.set(chosen)

    def _on_submit(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Repository name is required.", parent=self.dialog)
            return

        desc = self.desc_entry.get().strip()
        private = self.vis_var.get() == "private"
        readme = self.readme_var.get()

        gi = self.gitignore_var.get()
        gi_val = gi if gi != "None" else None

        lic = self.license_var.get()
        lic_val = lic if lic != "None" else None

        clone_path = self.clone_path_var.get().strip() if self.clone_var.get() else None

        self.submit_btn.config(state=tk.DISABLED, text="Creating...")
        try:
            out = self.gh_manager.repos.create_repo(
                name=name,
                description=desc,
                private=private,
                init_readme=readme,
                gitignore=gi_val,
                license=lic_val,
                clone_path=clone_path,
            )
            messagebox.showinfo("Success", f"Repository '{name}' created successfully!", parent=self.dialog)
            self.dialog.destroy()
            if self.on_created:
                self.on_created(name)
        except Exception as e:
            messagebox.showerror("Error Creating Repository", str(e), parent=self.dialog)
            self.submit_btn.config(state=tk.NORMAL, text="Create")
