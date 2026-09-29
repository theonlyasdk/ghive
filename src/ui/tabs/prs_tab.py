"""Pull requests tab for reviewing and managing pull requests."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import CreatePRDialog, PRDetailsDialog
from ui.widgets import EmptyState, LoadingOverlay, SearchEntry


class PRsTab(ttk.Frame):
    """Tab for listing, searching, reviewing, and merging pull requests."""

    def __init__(
        self,
        parent: tk.Widget,
        gh_manager: GHManager,
        async_runner: AsyncRunner,
        set_status: Callable[[str], None],
    ):
        super().__init__(parent)
        self.gh_manager = gh_manager
        self.async_runner = async_runner
        self.set_status = set_status
        self.config = ConfigManager()

        self.current_repo: str = ""
        self.prs: List[Dict[str, Any]] = []
        self.filtered_prs: List[Dict[str, Any]] = []
        self.selected_pr: Optional[Dict[str, Any]] = None
        self._sort_col: str = "#"
        self._sort_reverse: bool = True

        self._create_ui()

    def _create_ui(self) -> None:
        # Top toolbar
        toolbar = ttk.Frame(self, padding=(6, 6))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Repo:").pack(side=tk.LEFT, padx=(0, 4))
        self.repo_var = tk.StringVar()
        self.repo_cb = ttk.Combobox(toolbar, textvariable=self.repo_var, width=24)
        self.repo_cb.pack(side=tk.LEFT, padx=(0, 8))
        self.repo_cb.bind("<Return>", lambda e: self.refresh())
        self.repo_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.search_entry = SearchEntry(toolbar, placeholder="Search pull requests...", on_search=self._filter_list, width=22)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="State:").pack(side=tk.LEFT, padx=(0, 4))
        self.state_var = tk.StringVar(value="open")
        state_cb = ttk.Combobox(toolbar, textvariable=self.state_var, values=["open", "closed", "merged", "all"], state="readonly", width=8)
        state_cb.pack(side=tk.LEFT, padx=(0, 8))
        state_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side=tk.RIGHT)

        # Main Content Area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("#", "Title", "Author", "Branches", "Updated")
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        self.tree.column("#", width=60, anchor="center")
        self.tree.column("Title", width=360)
        self.tree.column("Author", width=110, anchor="center")
        self.tree.column("Branches", width=160)
        self.tree.column("Updated", width=120, anchor="center")

        tree_scroll = ttk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._view_details())
        self.tree.bind("<Return>", lambda e: self._view_details())

        # Context Menu
        self._create_context_menu()

        # Empty State
        self.empty_state = EmptyState(
            self.content_frame,
            title="No Pull Requests Found",
            instructions=[
                "Select a repository or enter an 'owner/repo' above to browse pull requests.",
                "Click 'New PR...' below to propose changes.",
            ],
            action_text="Create Pull Request",
            action_command=self._new_pr,
        )

        # Bottom Button Bar
        self.btn_bar = ttk.Frame(self, padding=(6, 6))
        self.btn_bar.pack(fill=tk.X)

        self.new_btn = ttk.Button(self.btn_bar, text="New PR...", command=self._new_pr)
        self.new_btn.pack(side=tk.LEFT, padx=2)

        self.details_btn = ttk.Button(self.btn_bar, text="View Details & Diff", command=self._view_details, state=tk.DISABLED)
        self.details_btn.pack(side=tk.LEFT, padx=2)

        self.checkout_btn = ttk.Button(self.btn_bar, text="Checkout", command=self._checkout_pr, state=tk.DISABLED)
        self.checkout_btn.pack(side=tk.LEFT, padx=2)

        self.merge_btn = ttk.Button(self.btn_bar, text="Merge...", command=self._merge_pr, state=tk.DISABLED)
        self.merge_btn.pack(side=tk.LEFT, padx=2)

        self.web_btn = ttk.Button(self.btn_bar, text="Open in Browser", command=self._open_in_browser, state=tk.DISABLED)
        self.web_btn.pack(side=tk.LEFT, padx=2)

        self.loading_overlay = LoadingOverlay(self)
        if self.config.get("general", "active_repo", ""):
            self.content_frame.pack_forget()
            self.btn_bar.pack_forget()
            self.loading_overlay.show()

    def _create_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details & Diff", command=self._view_details)
        self.context_menu.add_command(label="Checkout Branch Locally", command=self._checkout_pr)
        self.context_menu.add_command(label="Merge Pull Request...", command=self._merge_pr)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open in Browser", command=self._open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy PR #", command=self._copy_number)
        self.context_menu.add_command(label="Copy Title", command=self._copy_title)
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)

        def show_menu(event):
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self._on_select()
                self.context_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", show_menu)

    def set_active_repo(self, repo_name: str) -> None:
        """Update active repository and refresh if changed."""
        if not repo_name:
            return
        current = self.repo_var.get().strip()
        existing = list(self.repo_cb["values"])
        if repo_name not in existing:
            self.repo_cb["values"] = [repo_name] + existing

        if current != repo_name:
            self.repo_var.set(repo_name)
            self.current_repo = repo_name
            self.refresh()

    def refresh(self) -> None:
        """Fetch pull requests for current repository asynchronously."""
        repo = self.repo_var.get().strip()
        if not repo:
            self.prs = []
            self.filtered_prs = []
            self._populate_tree()
            return

        self.current_repo = repo
        state = self.state_var.get()
        self.set_status(f"Fetching pull requests for {repo}...")
        self.refresh_btn.config(state=tk.DISABLED)

        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

        limit = self.config.get("general", "default_limit", 30)

        def _task():
            return self.gh_manager.prs.list_prs(repo=repo, state=state, limit=limit)

        def _on_success(data):
            self.prs = data
            self._filter_list(self.search_entry.get_query())
            self.set_status(f"Loaded {len(data)} pull requests for {repo}")

        def _on_error(exc):
            self.set_status(f"Error fetching PRs: {exc}")
            messagebox.showerror("Error", f"Failed to fetch pull requests:\n{exc}", parent=self.winfo_toplevel())

        def _on_complete():
            self.loading_overlay.hide()
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
            self.btn_bar.pack(fill=tk.X)
            self.refresh_btn.config(state=tk.NORMAL)

        self.async_runner.run(_task, on_success=_on_success, on_error=_on_error, on_complete=_on_complete)

    def _filter_list(self, query: str = "") -> None:
        q = query.strip().lower()
        if not q:
            self.filtered_prs = list(self.prs)
        else:
            self.filtered_prs = [
                p for p in self.prs
                if q in str(p.get("number", "")) or q in p.get("title", "").lower()
            ]

        self._populate_tree()

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.filtered_prs:
            self.tree.pack_forget()
            self.empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_button_states()
            return

        self.empty_state.pack_forget()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for pr in self.filtered_prs:
            num = f"#{pr.get('number', '')}"
            title = pr.get("title", "")
            author = pr.get("author", {}).get("login", "unknown") if isinstance(pr.get("author"), dict) else "unknown"
            head = pr.get("headRefName", "")
            base = pr.get("baseRefName", "")
            branches = f"{head} → {base}" if head and base else head
            updated = pr.get("updatedAt", "").replace("T", " ").replace("Z", "")[:16]

            self.tree.insert("", tk.END, values=(num, title, author, branches, updated))

        self._update_button_states()

    def _sort_by_column(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_map = {
            "#": lambda p: p.get("number", 0),
            "Title": lambda p: p.get("title", "").lower(),
            "Author": lambda p: (p.get("author", {}).get("login", "") if isinstance(p.get("author"), dict) else "").lower(),
            "Branches": lambda p: p.get("headRefName", "").lower(),
            "Updated": lambda p: p.get("updatedAt", ""),
        }

        key_func = key_map.get(col, lambda p: "")
        self.filtered_prs.sort(key=key_func, reverse=self._sort_reverse)
        self._populate_tree()

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_pr = None
            self._update_button_states()
            return

        item = self.tree.item(selection[0])
        num_str = str(item["values"][0]).replace("#", "")
        matched = next((p for p in self.prs if str(p.get("number")) == num_str), None)
        self.selected_pr = matched
        self._update_button_states()

    def _update_button_states(self) -> None:
        has_sel = self.selected_pr is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.details_btn.config(state=state)
        self.checkout_btn.config(state=state)
        self.web_btn.config(state=state)

        if has_sel:
            is_open = self.selected_pr.get("state", "OPEN").upper() == "OPEN"
            self.merge_btn.config(state=tk.NORMAL if is_open else tk.DISABLED)
        else:
            self.merge_btn.config(state=tk.DISABLED)

    def _view_details(self) -> None:
        if not self.selected_pr:
            return
        num = self.selected_pr.get("number")
        PRDetailsDialog(self.winfo_toplevel(), self.current_repo, num, self.gh_manager, on_updated=self.refresh)

    def _new_pr(self) -> None:
        CreatePRDialog(self.winfo_toplevel(), self.current_repo, self.gh_manager, on_created=lambda r: self.refresh())

    def _checkout_pr(self) -> None:
        if not self.selected_pr:
            return
        num = self.selected_pr.get("number")
        self.set_status(f"Checking out PR #{num}...")
        try:
            out = self.gh_manager.prs.checkout_pr(self.current_repo, num)
            messagebox.showinfo("Checkout", f"Branch checked out successfully:\n{out}", parent=self.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Checkout Failed", str(e), parent=self.winfo_toplevel())

    def _merge_pr(self) -> None:
        if not self.selected_pr:
            return
        num = self.selected_pr.get("number")
        if self.config.get("confirmations", "confirm_merge_pr", True):
            if not messagebox.askyesno("Confirm Merge", f"Merge Pull Request #{num}?", parent=self.winfo_toplevel()):
                return

        self.set_status(f"Merging PR #{num}...")
        try:
            self.gh_manager.prs.merge_pr(self.current_repo, num)
            messagebox.showinfo("Success", f"PR #{num} merged successfully!", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Merge Failed", str(e), parent=self.winfo_toplevel())

    def _open_in_browser(self) -> None:
        if not self.selected_pr:
            return
        url = self.selected_pr.get("url") or f"https://github.com/{self.current_repo}/pull/{self.selected_pr.get('number')}"
        self.gh_manager.open_in_browser(url)

    def _copy_number(self) -> None:
        if self.selected_pr:
            self.clipboard_clear()
            self.clipboard_append(str(self.selected_pr.get("number", "")))

    def _copy_title(self) -> None:
        if self.selected_pr:
            self.clipboard_clear()
            self.clipboard_append(self.selected_pr.get("title", ""))

    def _copy_url(self) -> None:
        if self.selected_pr:
            url = self.selected_pr.get("url") or f"https://github.com/{self.current_repo}/pull/{self.selected_pr.get('number')}"
            self.clipboard_clear()
            self.clipboard_append(url)
