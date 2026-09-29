"""In-dialog error view widget with retry and close actions."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ErrorView(ttk.Frame):
    """Widget displaying a clean error state inside a dialog with a retry button."""

    def __init__(
        self,
        parent: tk.Widget,
        on_retry: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.on_retry = on_retry
        self.on_close = on_close

        self.center_box = ttk.Frame(self, padding=24)
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        self.title_lbl = ttk.Label(
            self.center_box,
            text="Failed to load content",
            font=("Segoe UI", 12, "bold"),
            foreground="#cf222e",
            anchor="center",
        )
        self.title_lbl.pack(pady=(0, 8))

        self.msg_text = tk.Text(
            self.center_box,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            foreground="#57606a",
            background="#f6f8fa",
            relief=tk.SOLID,
            bd=1,
            width=50,
            height=4,
        )
        self.msg_text.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        btn_row = ttk.Frame(self.center_box)
        btn_row.pack()

        if self.on_retry:
            self.retry_btn = ttk.Button(btn_row, text="Retry", command=self.on_retry, width=12)
            self.retry_btn.pack(side=tk.LEFT, padx=4)

        if self.on_close:
            self.close_btn = ttk.Button(btn_row, text="Close", command=self.on_close, width=12)
            self.close_btn.pack(side=tk.LEFT, padx=4)

    def show(self, error_message: str = "An unexpected error occurred.") -> None:
        """Display the error view with the provided message."""
        self.msg_text.config(state=tk.NORMAL)
        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", error_message.strip())
        self.msg_text.config(state=tk.DISABLED)
        self.pack(fill=tk.BOTH, expand=True)

    def hide(self) -> None:
        """Hide the error view."""
        self.pack_forget()
