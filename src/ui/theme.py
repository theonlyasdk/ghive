"""UI styling and theme configuration for ghive."""

import platform
import tkinter as tk
from tkinter import ttk


def setup_theme(root: tk.Tk) -> None:
    """Configure modern native ttk styles."""
    style = ttk.Style(root)

    # Use native system theme where available
    system = platform.system().lower()
    available = style.theme_names()
    if system == "windows" and "vista" in available:
        style.theme_use("vista")
    elif system == "darwin" and "aqua" in available:
        style.theme_use("aqua")
    elif "clam" in available:
        style.theme_use("clam")

    # Font definitions
    base_font = ("Segoe UI", 9) if system == "windows" else ("Helvetica", 10)
    bold_font = ("Segoe UI", 9, "bold") if system == "windows" else ("Helvetica", 10, "bold")
    header_font = ("Segoe UI", 12, "bold") if system == "windows" else ("Helvetica", 13, "bold")
    mono_font = ("Consolas", 9) if system == "windows" else ("Menlo", 10)

    # Lighter and larger variant fonts (8pt larger than standard headings)
    empty_title_family = "Segoe UI Light" if system == "windows" else ("Helvetica Neue Light" if system == "darwin" else "Ubuntu Light")
    empty_title_font = (empty_title_family, 21)
    light_header_font = (empty_title_family, 19)

    # Configure treeview
    style.configure(
        "Treeview",
        font=base_font,
        rowheight=26,
    )
    style.configure(
        "Treeview.Heading",
        font=bold_font,
        padding=4,
    )

    # Configure notebook tabs
    style.configure(
        "TNotebook.Tab",
        font=base_font,
        padding=[12, 6],
    )

    # Configure buttons
    style.configure(
        "TButton",
        font=base_font,
        padding=[8, 4],
    )

    # Accent button for primary actions
    style.configure(
        "Accent.TButton",
        font=bold_font,
        padding=[10, 4],
    )

    # Store fonts on root for convenient reuse in dialogs
    root.app_font_base = base_font
    root.app_font_bold = bold_font
    root.app_font_header = header_font
    root.app_font_mono = mono_font
    root.app_font_empty_title = empty_title_font
    root.app_font_light_header = light_header_font
    root.app_font_loading = (empty_title_family, 24)
