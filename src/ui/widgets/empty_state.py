"""Instructional placeholder frame for empty list states."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional


class EmptyState(ttk.Frame):
    """Clean empty state view displaying title, instructions, and an optional action button."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "No Items Found",
        instructions: Optional[List[str]] = None,
        action_text: Optional[str] = None,
        action_command: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.action_command = action_command

        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        title_font = getattr(parent.winfo_toplevel(), "app_font_empty_title", ("Segoe UI Light", 21))
        base_font = getattr(parent.winfo_toplevel(), "app_font_base", ("Segoe UI", 9))

        title_label = tk.Label(
            container,
            text=title,
            font=title_font,
            fg="#24292f",
        )
        title_label.pack(pady=(0, 12))

        if instructions:
            for line in instructions:
                lbl = tk.Label(
                    container,
                    text=line,
                    font=base_font,
                    fg="#57606a",
                    justify=tk.CENTER,
                )
                lbl.pack(pady=1)

        if action_text and action_command:
            btn = ttk.Button(
                container,
                text=action_text,
                command=action_command,
            )
            btn.pack(pady=(16, 0))
