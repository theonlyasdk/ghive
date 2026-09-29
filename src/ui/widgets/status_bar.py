"""Status bar widget for application status and account indicator."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class StatusBar(ttk.Frame):
    """Bottom status bar with status message and user account button."""

    def __init__(
        self,
        parent: tk.Widget,
        on_auth_click: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, relief=tk.SUNKEN, padding=(4, 2))
        self.on_auth_click = on_auth_click

        base_font = getattr(parent.winfo_toplevel(), "app_font_base", ("Segoe UI", 9))

        self.status_label = ttk.Label(
            self,
            text="Ready",
            anchor=tk.W,
            font=base_font,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.account_btn = ttk.Button(
            self,
            text="Checking auth...",
            command=self._on_account_clicked,
            padding=(6, 1),
        )
        self.account_btn.pack(side=tk.RIGHT, padx=4)

    def _on_account_clicked(self) -> None:
        if self.on_auth_click:
            self.on_auth_click()

    def set_status(self, message: str, is_error: bool = False, is_warning: bool = False) -> None:
        """Update the main status text with optional alert coloring."""
        fg = "black"
        if is_error:
            fg = "#cf222e"
        elif is_warning:
            fg = "#9a6700"

        self.status_label.config(text=message, foreground=fg)

    def set_user_info(self, user: str, host: str = "github.com", logged_in: bool = True) -> None:
        """Update the user account display button."""
        if logged_in and user and user != "Unknown":
            self.account_btn.config(text=f"@{user} ({host})", state=tk.NORMAL)
        elif logged_in:
            self.account_btn.config(text=f"Logged in ({host})", state=tk.NORMAL)
        else:
            self.account_btn.config(text="Not logged in", state=tk.NORMAL)
