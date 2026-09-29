import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core import ConfigManager, GHManager
from ui.widgets import ErrorView, LoadingOverlay, MarkdownText


class PRDetailsDialog:
    """Dialog displaying pull request overview, diff viewer, checks, and merge actions."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        pr_number: int,
        gh_manager: GHManager,
        on_updated: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.pr_number = pr_number
        self.gh_manager = gh_manager
        self.on_updated = on_updated
        self.config = ConfigManager()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Pull Request #{pr_number} - {repo}")
        self.dialog.geometry("700x620")
        self.dialog.minsize(600, 500)
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
            dw = 700
            dh = 620
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

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 4))

        self.title_lbl = tk.Label(header, text=f"#{self.pr_number} Loading...", font=("Segoe UI", 12, "bold"), anchor=tk.W, fg="#0969da")
        self.title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.state_badge = tk.Label(header, text="[...]", font=("Segoe UI", 9, "bold"), fg="#57606a")
        self.state_badge.pack(side=tk.RIGHT)

        self.meta_lbl = tk.Label(container, text="", font=("Segoe UI", 8), fg="#57606a", anchor=tk.W)
        self.meta_lbl.pack(fill=tk.X, pady=(0, 8))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Overview Tab
        overview_tab = ttk.Frame(notebook, padding=6)
        notebook.add(overview_tab, text="Overview")

        self.body_text = MarkdownText(overview_tab)
        body_scroll = ttk.Scrollbar(overview_tab, orient=tk.VERTICAL, command=self.body_text.yview)
        self.body_text.configure(yscrollcommand=body_scroll.set)
        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Diff Tab
        diff_tab = ttk.Frame(notebook, padding=6)
        notebook.add(diff_tab, text="Diff")

        self.diff_text = tk.Text(diff_tab, wrap=tk.NONE, font=("Consolas", 9), relief=tk.SOLID, bd=1)
        diff_scroll_y = ttk.Scrollbar(diff_tab, orient=tk.VERTICAL, command=self.diff_text.yview)
        diff_scroll_x = ttk.Scrollbar(diff_tab, orient=tk.HORIZONTAL, command=self.diff_text.xview)
        self.diff_text.configure(yscrollcommand=diff_scroll_y.set, xscrollcommand=diff_scroll_x.set)

        self.diff_text.tag_configure("add", foreground="#1a7f37", background="#e6ffed")
        self.diff_text.tag_configure("del", foreground="#cf222e", background="#ffebe9")
        self.diff_text.tag_configure("meta", foreground="#0969da", font=("Consolas", 9, "bold"))

        diff_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        diff_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.diff_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bottom Bar
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Open in Browser", command=self._open_web, width=14).pack(side=tk.RIGHT, padx=6)

        self.merge_btn = ttk.Button(btn_bar, text="Merge PR...", command=self._on_merge_clicked, width=12)
        self.merge_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.toggle_state_btn = ttk.Button(btn_bar, text="Toggle State", command=self._toggle_state, width=12)
        self.toggle_state_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(btn_bar, text="Checkout Branch", command=self._checkout_branch, width=15).pack(side=tk.LEFT)

    def _load_details(self) -> None:
        self.loading_overlay.show()
        self.error_view.hide()
        self.main_container.pack_forget()

        def _worker():
            try:
                data = self.gh_manager.prs.view_pr(self.repo, self.pr_number)
                diff = self.gh_manager.prs.get_diff(self.repo, self.pr_number)
                self.dialog.after(0, lambda d=data, df=diff: self._on_details_loaded(d, df))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: self._on_details_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_details_loaded(self, data: Dict[str, Any], diff_content: str) -> None:
        self.loading_overlay.hide()
        self.error_view.hide()
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.data = data

        title = data.get("title", f"Pull Request #{self.pr_number}")
        self.title_lbl.config(text=f"#{self.pr_number} {title}")

        state = data.get("state", "OPEN").upper()
        if state == "MERGED":
            self.state_badge.config(text="[MERGED]", fg="#8250df")
            self.merge_btn.config(state=tk.DISABLED)
            self.toggle_state_btn.config(state=tk.DISABLED)
        elif state == "OPEN":
            self.state_badge.config(text="[OPEN]", fg="#1a7f37")
            self.merge_btn.config(state=tk.NORMAL)
            self.toggle_state_btn.config(text="Close PR", state=tk.NORMAL)
        else:
            self.state_badge.config(text=f"[{state}]", fg="#cf222e")
            self.merge_btn.config(state=tk.DISABLED)
            self.toggle_state_btn.config(text="Reopen PR", state=tk.NORMAL)

        head = data.get("headRefName", "branch")
        base = data.get("baseRefName", "main")
        author = data.get("author", {}).get("login", "unknown") if isinstance(data.get("author"), dict) else "unknown"
        created = data.get("createdAt", "").replace("T", " ").replace("Z", "")
        draft = " (Draft)" if data.get("isDraft") else ""

        self.meta_lbl.config(text=f"{head} → {base}{draft} | By @{author} on {created}")

        body = data.get("body") or "(No description provided)"
        self.body_text.set_markdown(body)

        self._populate_diff(diff_content)

    def _on_details_error(self, err_msg: str) -> None:
        self.loading_overlay.hide()
        self.main_container.pack_forget()
        self.error_view.show(f"Failed to load PR details:\n{err_msg}")

    def _populate_diff(self, diff_content: str) -> None:
        self.diff_text.config(state=tk.NORMAL)
        self.diff_text.delete("1.0", tk.END)
        if not diff_content:
            self.diff_text.insert("1.0", "(No diff available)")
        else:
            for line in diff_content.splitlines():
                if line.startswith("+++") or line.startswith("---") or line.startswith("diff "):
                    self.diff_text.insert(tk.END, line + "\n", ("meta",))
                elif line.startswith("+"):
                    self.diff_text.insert(tk.END, line + "\n", ("add",))
                elif line.startswith("-"):
                    self.diff_text.insert(tk.END, line + "\n", ("del",))
                else:
                    self.diff_text.insert(tk.END, line + "\n")
        self.diff_text.config(state=tk.DISABLED)

    def _on_merge_clicked(self) -> None:
        if self.config.get("confirmations", "confirm_merge_pr", True):
            if not messagebox.askyesno("Confirm Merge", f"Merge Pull Request #{self.pr_number}?", parent=self.dialog):
                return

        self.merge_btn.config(state=tk.DISABLED, text="Merging...")
        try:
            self.gh_manager.prs.merge_pr(self.repo, self.pr_number, method="merge")
            messagebox.showinfo("Success", f"PR #{self.pr_number} merged successfully!", parent=self.dialog)
            self._load_details()
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Merge Failed", str(e), parent=self.dialog)
            self.merge_btn.config(state=tk.NORMAL, text="Merge PR...")

    def _toggle_state(self) -> None:
        state = self.data.get("state", "OPEN").upper()
        if state == "OPEN":
            if self.config.get("confirmations", "confirm_close_pr", True):
                if not messagebox.askyesno("Confirm Close", f"Close PR #{self.pr_number}?", parent=self.dialog):
                    return
            try:
                self.gh_manager.prs.close_pr(self.repo, self.pr_number)
                self._load_details()
                if self.on_updated:
                    self.on_updated()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)
        else:
            try:
                self.gh_manager.prs.reopen_pr(self.repo, self.pr_number)
                self._load_details()
                if self.on_updated:
                    self.on_updated()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)

    def _checkout_branch(self) -> None:
        try:
            out = self.gh_manager.prs.checkout_pr(self.repo, self.pr_number)
            messagebox.showinfo("Checkout", f"Branch checked out successfully:\n{out}", parent=self.dialog)
        except Exception as e:
            messagebox.showerror("Checkout Failed", str(e), parent=self.dialog)

    def _open_web(self) -> None:
        url = getattr(self, "data", {}).get("url") or f"https://github.com/{self.repo}/pull/{self.pr_number}"
        self.gh_manager.open_in_browser(url)
