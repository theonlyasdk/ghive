"""GitHub-style comment card widget for issues and pull requests."""

import platform
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ui.widgets.markdown_text import MarkdownText


class CommentCard(tk.Frame):
    """Card container representing a single GitHub issue description or comment."""

    def __init__(
        self,
        parent: tk.Widget,
        author: str,
        created_at: str,
        body: str,
        is_opener: bool = False,
        badge: Optional[str] = None,
        scroll_target: Optional[tk.Canvas] = None,
        issue_url: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            highlightbackground="#d0d7de",
            highlightthickness=1,
            background="#ffffff",
            **kwargs,
        )

        self.author = author
        self.created_at = created_at
        self.body = body
        self.is_opener = is_opener
        self.badge = badge
        self.scroll_target = scroll_target
        self.issue_url = issue_url

        system = platform.system().lower()
        self.base_font = "Segoe UI" if system == "windows" else ("Helvetica Neue" if system == "darwin" else "DejaVu Sans")

        self._create_header()
        self._create_body()


    def _create_header(self) -> None:
        header_frame = tk.Frame(self, background="#f6f8fa", padx=12, pady=8)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        # Left: Author & date
        left_box = tk.Frame(header_frame, background="#f6f8fa")
        left_box.pack(side=tk.LEFT)

        author_lbl = tk.Label(
            left_box,
            text=self.author,
            font=(self.base_font, 9, "bold"),
            foreground="#1f2328",
            background="#f6f8fa",
        )
        author_lbl.pack(side=tk.LEFT)

        action_phrase = "opened on" if self.is_opener else "commented on"
        date_display = self.created_at.split("T")[0] if "T" in self.created_at else self.created_at
        date_lbl = tk.Label(
            left_box,
            text=f" {action_phrase} {date_display}",
            font=(self.base_font, 9),
            foreground="#57606a",
            background="#f6f8fa",
        )
        date_lbl.pack(side=tk.LEFT)

        # Right: Badge (e.g. Owner, Author)
        if self.badge:
            badge_lbl = tk.Label(
                header_frame,
                text=self.badge,
                font=(self.base_font, 8, "bold"),
                foreground="#57606a",
                background="#f6f8fa",
                highlightbackground="#d0d7de",
                highlightthickness=1,
                padx=6,
                pady=1,
            )
            badge_lbl.pack(side=tk.RIGHT)

        # Bottom border of header
        sep = tk.Frame(self, height=1, background="#d0d7de")
        sep.pack(fill=tk.X, side=tk.TOP)

    def _create_body(self) -> None:
        body_container = tk.Frame(self, background="#ffffff", padx=14, pady=10)
        body_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.md_text = MarkdownText(
            body_container,
            wrap=tk.WORD,
            background="#ffffff",
            foreground="#1f2328",
            padx=2,
            pady=2,
        )
        self.md_text.pack(fill=tk.BOTH, expand=True)

        if not self.body or not self.body.strip():
            if self.is_opener:
                content = "*No description has been provided for this issue...*"
            else:
                content = "*(No comment content)*"
        else:
            content = self.body
        self.md_text.set_markdown(content)
        self.md_text.fit_height()

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Comment Text", command=self._copy_body)
        self.context_menu.add_command(label="Copy Issue Link", command=self._copy_issue_url, state=tk.NORMAL if self.issue_url else tk.DISABLED)
        for widget in (self, body_container, self.md_text):
            widget.bind("<Button-3>", self._show_context_menu)
            widget.bind("<Button-2>", self._show_context_menu)

        if self.scroll_target:
            self.md_text.bind("<MouseWheel>", self._on_mousewheel)
            self.bind("<MouseWheel>", self._on_mousewheel)

        self.bind("<Configure>", self._on_configure)

    def _show_context_menu(self, event) -> str:
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        return "break"

    def _copy_text(self, text: str) -> None:
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def _copy_body(self) -> None:
        self._copy_text(self.body)

    def _copy_issue_url(self) -> None:
        if self.issue_url:
            self._copy_text(self.issue_url)

    def _on_mousewheel(self, event) -> str:
        if self.scroll_target:
            try:
                self.scroll_target.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
            return "break"
        return ""

    def _on_configure(self, event=None) -> None:
        if event and event.width > 50:
            self.md_text.fit_height()
