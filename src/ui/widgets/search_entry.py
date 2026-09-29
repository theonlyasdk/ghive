"""Clean search entry with clear button and placeholder."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class SearchEntry(ttk.Frame):
    """Reusable search entry widget with placeholder and quick clear button."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "Search...",
        on_search: Optional[Callable[[str], None]] = None,
        width: int = 30,
    ):
        super().__init__(parent)
        self.placeholder = placeholder
        self.on_search = on_search
        self._has_placeholder = False

        self.var = tk.StringVar()

        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.clear_btn = ttk.Button(
            self,
            text="✕",
            width=2,
            command=self.clear,
        )

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<KeyRelease>", self._on_key_release)

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not self.var.get():
            self._has_placeholder = True
            self.entry.insert(0, self.placeholder)
            self.entry.config(foreground="gray")
            self.clear_btn.pack_forget()

    def _on_focus_in(self, event=None) -> None:
        if self._has_placeholder:
            self._has_placeholder = False
            self.entry.delete(0, tk.END)
            self.entry.config(foreground="black")

    def _on_focus_out(self, event=None) -> None:
        if not self.entry.get().strip():
            self._show_placeholder()

    def _on_return(self, event=None) -> None:
        if self.on_search:
            text = "" if self._has_placeholder else self.entry.get().strip()
            self.on_search(text)

    def _on_key_release(self, event=None) -> None:
        if not self._has_placeholder and self.entry.get():
            if not self.clear_btn.winfo_ismapped():
                self.clear_btn.pack(side=tk.RIGHT, padx=(2, 0))
        else:
            self.clear_btn.pack_forget()

    def get_query(self) -> str:
        """Return the current search query."""
        if self._has_placeholder:
            return ""
        return self.entry.get().strip()

    def clear(self) -> None:
        """Clear search query and restore placeholder."""
        self.entry.delete(0, tk.END)
        self._show_placeholder()
        if self.on_search:
            self.on_search("")
