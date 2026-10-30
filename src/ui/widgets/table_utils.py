"""Shared Treeview helpers for sort indicators and context-menu state."""

import tkinter as tk
from tkinter import ttk
from typing import Iterable, Mapping, Optional

SORT_ASC = "\u25b2"
SORT_DESC = "\u25bc"


def apply_sort_indicator(
    tree: ttk.Treeview,
    columns: Iterable[str],
    sort_col: Optional[str],
    reverse: bool,
) -> None:
    """Show an ascending/descending arrow on the active sort column."""
    marker = SORT_DESC if reverse else SORT_ASC
    for col in columns:
        text = f"{col} {marker}" if col == sort_col else col
        tree.heading(col, text=text)


def set_menu_item_state(menu: tk.Menu, label: str, enabled: bool) -> None:
    """Enable or disable a context-menu entry by its label."""
    try:
        menu.entryconfig(label, state=tk.NORMAL if enabled else tk.DISABLED)
    except tk.TclError:
        # The menu entry no longer exists (or was relabeled); ignore.
        pass


def set_menu_items_state(menu: tk.Menu, states: Mapping[str, bool]) -> None:
    """Apply enabled/disabled state to several context-menu entries at once."""
    for label, enabled in states.items():
        set_menu_item_state(menu, label, enabled)
