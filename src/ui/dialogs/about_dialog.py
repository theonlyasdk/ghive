"""About dialog for ghive."""

import tkinter as tk
from tkinter import ttk


class AboutDialog:
    """Dialog displaying application information, features, and licensing."""

    def __init__(self, parent: tk.Widget):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("About ghive")
        self.dialog.geometry("420x520")
        self.dialog.minsize(380, 480)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 420
            dh = 520
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
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(
            main_frame,
            text="ghive",
            font=("Segoe UI", 24, "bold"),
            fg="#0969da",
        )
        title.pack(pady=(0, 6))

        version = tk.Label(
            main_frame,
            text="Version 0.1.0",
            font=("Segoe UI", 10),
            fg="#57606a",
        )
        version.pack()

        desc = tk.Label(
            main_frame,
            text="Clean, accurate GUI frontend for GitHub CLI\nFast, lightweight, and native.",
            font=("Segoe UI", 10),
            justify=tk.CENTER,
            fg="#24292f",
        )
        desc.pack(pady=16)

        features_frame = ttk.LabelFrame(main_frame, text="Features", padding=12)
        features_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        features = [
            "• Repositories: Search, filter, clone, sync & create",
            "• Issues: Browse, inspect, comment, close & reopen",
            "• Pull Requests: Inspect diffs, checks & merge",
            "• Actions: Workflow runs status & live log viewer",
            "• Gists: Explore files, create & clone",
            "• Cross-platform: Windows, macOS & Linux",
        ]

        for feat in features:
            lbl = tk.Label(
                features_frame,
                text=feat,
                anchor=tk.W,
                font=("Segoe UI", 9),
                fg="#24292f",
            )
            lbl.pack(fill=tk.X, pady=2)

        info = tk.Label(
            main_frame,
            text="© 2026 ASDK\nLicensed under MIT License",
            font=("Segoe UI", 8),
            fg="gray",
            justify=tk.CENTER,
        )
        info.pack(pady=(12, 10))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()

        ttk.Button(
            btn_frame,
            text="Close",
            command=self.dialog.destroy,
            width=14,
        ).pack()

    def show(self) -> None:
        """Wait for the dialog to close."""
        self.dialog.wait_window()
