"""Clean search entry with clear button, placeholder, and debounced live search."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class SearchEntry(ttk.Frame):
    """Reusable search entry widget with placeholder, clear button, and live filtering."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "Search...",
        on_search: Optional[Callable[[str], None]] = None,
        width: int = 30,
        debounce_ms: int = 250,
    ):
        super().__init__(parent)
        self.placeholder = placeholder
        self.on_search = on_search
        self.debounce_ms = debounce_ms
        self._has_placeholder = False
        self._search_after_id: Optional[str] = None
        self._last_query = ""

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
        self.bind("<Destroy>", self._on_destroy, add="+")

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
        self._cancel_pending_search()
        self._emit_search(self.get_query(), force=True)

    def _on_key_release(self, event=None) -> None:
        # Return is handled synchronously; ignore its KeyRelease so we do not
        # schedule a duplicate search.
        if event is not None and event.keysym in ("Return", "KP_Enter"):
            return

        if self._has_placeholder:
            return

        if self.entry.get().strip():
            if not self.clear_btn.winfo_ismapped():
                self.clear_btn.pack(side=tk.RIGHT, padx=(2, 0))
        else:
            self.clear_btn.pack_forget()

        query = self.get_query()
        if not query:
            self._cancel_pending_search()
            self._emit_search("")
            return

        self._schedule_search()

    def _schedule_search(self) -> None:
        self._cancel_pending_search()
        try:
            self._search_after_id = self.after(self.debounce_ms, self._run_pending_search)
        except tk.TclError:
            self._search_after_id = None

    def _run_pending_search(self) -> None:
        self._search_after_id = None
        self._emit_search(self.get_query())

    def _cancel_pending_search(self) -> None:
        if self._search_after_id is None:
            return
        try:
            self.after_cancel(self._search_after_id)
        except tk.TclError:
            pass
        self._search_after_id = None

    def _emit_search(self, query: str, force: bool = False) -> None:
        if not force and query == self._last_query:
            return
        self._last_query = query
        if self.on_search:
            self.on_search(query)

    def _on_destroy(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        self._cancel_pending_search()

    def get_query(self) -> str:
        """Return the current search query."""
        if self._has_placeholder:
            return ""
        return self.entry.get().strip()

    def clear(self) -> None:
        """Clear search query, restore placeholder, and reset the current filter."""
        self._cancel_pending_search()
        self.entry.delete(0, tk.END)
        self._show_placeholder()
        self._emit_search("", force=True)
