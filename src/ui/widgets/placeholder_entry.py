"""Entry widget with embedded placeholder support."""

import tkinter as tk
from tkinter import ttk


class PlaceholderEntry(ttk.Entry):
    """ttk.Entry subclass that supports placeholder text styling."""

    def __init__(self, parent=None, placeholder: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self._is_placeholder = False

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not super().get() and self.placeholder:
            self._is_placeholder = True
            super().insert(0, self.placeholder)
            self.configure(foreground="#8c959f")

    def _on_focus_in(self, event=None) -> None:
        if self._is_placeholder:
            self._is_placeholder = False
            super().delete(0, tk.END)
            self.configure(foreground="black")

    def _on_focus_out(self, event=None) -> None:
        if not super().get():
            self._show_placeholder()

    def get(self) -> str:
        """Return the user text, or empty string if placeholder is active."""
        if self._is_placeholder:
            return ""
        return super().get()

    def set_text(self, text: str) -> None:
        """Programmatically set text while maintaining placeholder behavior."""
        if self._is_placeholder:
            self._is_placeholder = False
            super().delete(0, tk.END)
            self.configure(foreground="black")
        else:
            super().delete(0, tk.END)

        if text:
            super().insert(0, text)
        else:
            self._show_placeholder()
