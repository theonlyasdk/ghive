"""Issue details dialog with GitHub-style markdown comments and discussion."""

import platform
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core import ConfigManager, GHManager
from ui.widgets import CommentCard, ErrorView, LoadingOverlay


class IssueDetailsDialog:
    """Dialog displaying issue details, GitHub-style comments, and actions."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        issue_number: int,
        gh_manager: GHManager,
        on_updated: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.issue_number = issue_number
        self.gh_manager = gh_manager
        self.on_updated = on_updated
        self.config = ConfigManager()
        self.data: Dict[str, Any] = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Issue #{issue_number} - {repo}")
        self.dialog.geometry("740x640")
        self.dialog.minsize(600, 520)
        self.dialog.transient(parent)

        self._create_widgets()
        self._load_details()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 740
            dh = 640
            cx = px + (pw // 2) - (dw // 2)
            cy = py + (ph // 2) - (dh // 2)
            self.dialog.geometry(f"{dw}x{dh}+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

        try:
            self.dialog.grab_set()
        except Exception:
            pass
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def _create_widgets(self) -> None:
        self.loading_overlay = LoadingOverlay(self.dialog, text="Loading...")
        self.error_view = ErrorView(self.dialog, on_retry=self._load_details, on_close=self.dialog.destroy)

        self.main_container = ttk.Frame(self.dialog, padding=14)
        container = self.main_container
        container.pack(fill=tk.BOTH, expand=True)

        # Header area
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 6))

        # Title: Light font + 8pt larger size
        system = platform.system().lower()
        light_font = "Segoe UI Light" if system == "windows" else ("Helvetica Neue Light" if system == "darwin" else "Ubuntu Light")

        self.title_lbl = tk.Label(
            header,
            text=f"#{self.issue_number} Loading...",
            font=(light_font, 20),
            anchor=tk.W,
            fg="#1f2328",
            wraplength=600,
            justify=tk.LEFT,
        )
        self.title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.state_badge = tk.Label(
            header,
            text="[...]",
            font=("Segoe UI", 9, "bold"),
            fg="#57606a",
            padx=8,
            pady=2,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
        )
        self.state_badge.pack(side=tk.RIGHT, padx=(8, 0))

        # Subtitle meta row
        self.meta_lbl = tk.Label(container, text="", font=("Segoe UI", 9), fg="#57606a", anchor=tk.W)
        self.meta_lbl.pack(fill=tk.X, pady=(0, 10))

        # Discussion Timeline (Scrollable area)
        timeline_container = ttk.Frame(container)
        timeline_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(timeline_container, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(timeline_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.timeline_frame = ttk.Frame(self.canvas)

        self.timeline_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.timeline_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mouse wheel binding when hovering timeline
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Bottom Bar
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Open in Browser", command=self._open_web, width=14).pack(side=tk.RIGHT, padx=6)

        self.toggle_state_btn = ttk.Button(btn_bar, text="Toggle State", command=self._toggle_state, width=14)
        self.toggle_state_btn.pack(side=tk.LEFT)

    def _bind_mousewheel(self, event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _load_details(self) -> None:
        self.loading_overlay.show()
        self.error_view.hide()
        self.main_container.pack_forget()

        def _worker():
            try:
                data = self.gh_manager.issues.view_issue(self.repo, self.issue_number)
                self.dialog.after(0, lambda d=data: self._on_details_loaded(d))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: self._on_details_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_details_loaded(self, data: Dict[str, Any]) -> None:
        self.loading_overlay.hide()
        self.error_view.hide()
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.data = data

        title = data.get("title", f"Issue #{self.issue_number}")
        self.title_lbl.config(text=f"#{self.issue_number} {title}")

        state = data.get("state", "OPEN").upper()
        if state == "OPEN":
            self.state_badge.config(text="Open", fg="#1a7f37", background="#dafbe1")
            self.toggle_state_btn.config(text="Close Issue")
        else:
            self.state_badge.config(text=f"Closed", fg="#8250df", background="#f8eefc")
            self.toggle_state_btn.config(text="Reopen Issue")

        opener = data.get("author", {}).get("login", "unknown") if isinstance(data.get("author"), dict) else "unknown"
        created = data.get("createdAt", "").replace("T", " ").replace("Z", "")
        comments = data.get("comments", [])
        num_comments = len(comments)
        labels = [lbl.get("name", "") for lbl in data.get("labels", []) if isinstance(lbl, dict)]
        lbl_str = f" • Labels: {', '.join(labels)}" if labels else ""

        self.meta_lbl.config(text=f"@{opener} opened this on {created} • {num_comments} comment(s){lbl_str}")

        self._render_timeline(opener, created, data.get("body") or "", comments)

    def _on_details_error(self, err_msg: str) -> None:
        self.loading_overlay.hide()
        self.main_container.pack_forget()
        self.error_view.show(f"Failed to load issue details:\n{err_msg}")

    def _render_timeline(self, opener: str, created: str, body: str, comments: list) -> None:
        for widget in self.timeline_frame.winfo_children():
            widget.destroy()

        repo_owner = self.repo.split("/")[0] if "/" in self.repo else ""
        issue_url = getattr(self, "data", {}).get("url") or f"https://github.com/{self.repo}/issues/{self.issue_number}"

        # 1. Opener Card (Issue Description)
        opener_badge = "Owner" if opener == repo_owner else "Author"
        desc_card = CommentCard(
            self.timeline_frame,
            author=opener,
            created_at=created,
            body=body,
            is_opener=True,
            badge=opener_badge,
            scroll_target=self.canvas,
            issue_url=issue_url,
        )
        desc_card.pack(fill=tk.X, expand=True, pady=(0, 12))

        # 2. Subsequent Comments
        for c in comments:
            c_author = c.get("author", {}).get("login", "unknown") if isinstance(c.get("author"), dict) else "unknown"
            c_date = c.get("createdAt", "").replace("T", " ").replace("Z", "")
            c_body = c.get("body", "")

            badge = None
            if c_author == repo_owner:
                badge = "Owner"
            elif c_author == opener:
                badge = "Author"

            card = CommentCard(
                self.timeline_frame,
                author=c_author,
                created_at=c_date,
                body=c_body,
                is_opener=False,
                badge=badge,
                scroll_target=self.canvas,
                issue_url=issue_url,
            )
            card.pack(fill=tk.X, expand=True, pady=(0, 12))

        # 3. Add a Comment Card at bottom
        self._create_comment_box()

        self.dialog.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _create_comment_box(self) -> None:
        box = tk.Frame(self.timeline_frame, highlightbackground="#d0d7de", highlightthickness=1, background="#ffffff")
        box.pack(fill=tk.X, expand=True, pady=(4, 16))

        hdr = tk.Frame(box, background="#f6f8fa", padx=12, pady=6)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Add a comment", font=("Segoe UI", 9, "bold"), fg="#1f2328", bg="#f6f8fa").pack(side=tk.LEFT)
        tk.Frame(box, height=1, background="#d0d7de").pack(fill=tk.X)

        body_frame = tk.Frame(box, background="#ffffff", padx=10, pady=8)
        body_frame.pack(fill=tk.BOTH, expand=True)

        self.new_comment_text = tk.Text(
            body_frame,
            height=4,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            foreground="#1f2328",
            background="#ffffff",
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
        )
        self.new_comment_text.pack(fill=tk.X, pady=(0, 8))

        btn_row = tk.Frame(body_frame, background="#ffffff")
        btn_row.pack(fill=tk.X)

        self.post_btn = ttk.Button(btn_row, text="Comment", command=self._post_comment)
        self.post_btn.pack(side=tk.RIGHT)

    def _post_comment(self) -> None:
        body = self.new_comment_text.get("1.0", tk.END).strip()
        if not body:
            return

        self.post_btn.config(state=tk.DISABLED)
        try:
            self.gh_manager.issues.comment_issue(self.repo, self.issue_number, body)
            self.new_comment_text.delete("1.0", tk.END)
            self._load_details()
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post comment:\n{e}", parent=self.dialog)
        finally:
            self.post_btn.config(state=tk.NORMAL)

    def _toggle_state(self) -> None:
        state = self.data.get("state", "OPEN").upper()
        if state == "OPEN":
            if self.config.get("confirmations", "confirm_close_issue", True):
                if not messagebox.askyesno("Confirm Close", f"Close issue #{self.issue_number}?", parent=self.dialog):
                    return
            try:
                self.gh_manager.issues.close_issue(self.repo, self.issue_number)
                self._load_details()
                if self.on_updated:
                    self.on_updated()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)
        else:
            try:
                self.gh_manager.issues.reopen_issue(self.repo, self.issue_number)
                self._load_details()
                if self.on_updated:
                    self.on_updated()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)

    def _open_web(self) -> None:
        url = getattr(self, "data", {}).get("url") or f"https://github.com/{self.repo}/issues/{self.issue_number}"
        self.gh_manager.open_in_browser(url)
