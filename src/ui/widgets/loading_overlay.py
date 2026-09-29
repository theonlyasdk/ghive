"""Loading overlay widget showing clean light text while data loads."""

import platform
import tkinter as tk
from tkinter import ttk


class LoadingOverlay(ttk.Frame):
    """Widget displaying a light, large 'Loading...' state while hiding tab content."""

    def __init__(self, parent: tk.Widget, text: str = "Loading..."):
        super().__init__(parent)
        self.text = text

        system = platform.system().lower()
        family = "Segoe UI Light" if system == "windows" else ("Helvetica Neue Light" if system == "darwin" else "Ubuntu Light")
        loading_font = getattr(parent.winfo_toplevel(), "app_font_loading", (family, 24))

        self.label = ttk.Label(
            self,
            text=self.text,
            font=loading_font,
            foreground="#57606a",
            anchor="center",
            justify=tk.CENTER,
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

    def show(self) -> None:
        """Display the loading overlay filling available space."""
        self.pack(fill=tk.BOTH, expand=True)

    def hide(self) -> None:
        """Hide the loading overlay."""
        self.pack_forget()
