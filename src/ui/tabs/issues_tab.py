"""Issues tab for browsing and managing GitHub repository issues."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import CreateIssueDialog, IssueDetailsDialog
from ui.widgets import EmptyState, LoadingOverlay, SearchEntry


class IssuesTab(ttk.Frame):
    """Tab for listing, searching, creating, and viewing repository issues."""

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
        self.issues: List[Dict[str, Any]] = []
        self.filtered_issues: List[Dict[str, Any]] = []
        self.selected_issue: Optional[Dict[str, Any]] = None
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

        self.search_entry = SearchEntry(toolbar, placeholder="Search issues...", on_search=self._filter_list, width=22)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="State:").pack(side=tk.LEFT, padx=(0, 4))
        self.state_var = tk.StringVar(value="open")
        state_cb = ttk.Combobox(toolbar, textvariable=self.state_var, values=["open", "closed", "all"], state="readonly", width=8)
        state_cb.pack(side=tk.LEFT, padx=(0, 8))
        state_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side=tk.RIGHT)

        # Main Content Area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("#", "Title", "Author", "Labels", "Updated")
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        self.tree.column("#", width=60, anchor="center")
        self.tree.column("Title", width=380)
        self.tree.column("Author", width=110, anchor="center")
        self.tree.column("Labels", width=140)
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
            title="No Issues Found",
            instructions=[
                "Select a repository from the Repositories tab or enter an 'owner/repo' above.",
                "Click 'New Issue...' to report a new problem or feature request.",
            ],
            action_text="Create Issue",
            action_command=self._new_issue,
        )

        # Bottom Button Bar
        self.btn_bar = ttk.Frame(self, padding=(6, 6))
        self.btn_bar.pack(fill=tk.X)

        self.new_btn = ttk.Button(self.btn_bar, text="New Issue...", command=self._new_issue)
        self.new_btn.pack(side=tk.LEFT, padx=2)

        self.details_btn = ttk.Button(self.btn_bar, text="View Details", command=self._view_details, state=tk.DISABLED)
        self.details_btn.pack(side=tk.LEFT, padx=2)

        self.toggle_state_btn = ttk.Button(self.btn_bar, text="Close Issue", command=self._toggle_state, state=tk.DISABLED)
        self.toggle_state_btn.pack(side=tk.LEFT, padx=2)

        self.web_btn = ttk.Button(self.btn_bar, text="Open in Browser", command=self._open_in_browser, state=tk.DISABLED)
        self.web_btn.pack(side=tk.LEFT, padx=2)

        self.loading_overlay = LoadingOverlay(self)
        if self.config.get("general", "active_repo", ""):
            self.content_frame.pack_forget()
            self.btn_bar.pack_forget()
            self.loading_overlay.show()

    def _create_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self._view_details)
        self.context_menu.add_command(label="Close / Reopen", command=self._toggle_state)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open in Browser", command=self._open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Issue #", command=self._copy_number)
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
        """Fetch issues for current repository asynchronously."""
        repo = self.repo_var.get().strip()
        if not repo:
            self.issues = []
            self.filtered_issues = []
            self._populate_tree()
            return

        self.current_repo = repo
        state = self.state_var.get()
        self.set_status(f"Fetching issues for {repo}...")
        self.refresh_btn.config(state=tk.DISABLED)

        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

        limit = self.config.get("general", "default_limit", 30)

        def _task():
            return self.gh_manager.issues.list_issues(repo=repo, state=state, limit=limit)

        def _on_success(data):
            self.issues = data
            self._filter_list(self.search_entry.get_query())
            self.set_status(f"Loaded {len(data)} issues for {repo}")

        def _on_error(exc):
            self.set_status(f"Error fetching issues: {exc}")
            messagebox.showerror("Error", f"Failed to fetch issues:\n{exc}", parent=self.winfo_toplevel())

        def _on_complete():
            self.loading_overlay.hide()
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
            self.btn_bar.pack(fill=tk.X)
            self.refresh_btn.config(state=tk.NORMAL)

        self.async_runner.run(_task, on_success=_on_success, on_error=_on_error, on_complete=_on_complete)

    def _filter_list(self, query: str = "") -> None:
        q = query.strip().lower()
        if not q:
            self.filtered_issues = list(self.issues)
        else:
            self.filtered_issues = [
                i for i in self.issues
                if q in str(i.get("number", "")) or q in i.get("title", "").lower()
            ]

        self._populate_tree()

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.filtered_issues:
            self.tree.pack_forget()
            self.empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_button_states()
            return

        self.empty_state.pack_forget()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for issue in self.filtered_issues:
            num = f"#{issue.get('number', '')}"
            title = issue.get("title", "")
            author = issue.get("author", {}).get("login", "unknown") if isinstance(issue.get("author"), dict) else "unknown"
            labels = [l.get("name", "") for l in issue.get("labels", []) if isinstance(l, dict)]
            lbl_str = ", ".join(labels)
            updated = issue.get("updatedAt", "").replace("T", " ").replace("Z", "")[:16]

            self.tree.insert("", tk.END, values=(num, title, author, lbl_str, updated))

        self._update_button_states()

    def _sort_by_column(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_map = {
            "#": lambda i: i.get("number", 0),
            "Title": lambda i: i.get("title", "").lower(),
            "Author": lambda i: (i.get("author", {}).get("login", "") if isinstance(i.get("author"), dict) else "").lower(),
            "Labels": lambda i: len(i.get("labels", [])),
            "Updated": lambda i: i.get("updatedAt", ""),
        }

        key_func = key_map.get(col, lambda i: "")
        self.filtered_issues.sort(key=key_func, reverse=self._sort_reverse)
        self._populate_tree()

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_issue = None
            self._update_button_states()
            return

        item = self.tree.item(selection[0])
        num_str = str(item["values"][0]).replace("#", "")
        matched = next((i for i in self.issues if str(i.get("number")) == num_str), None)
        self.selected_issue = matched
        self._update_button_states()

    def _update_button_states(self) -> None:
        has_sel = self.selected_issue is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.details_btn.config(state=state)
        self.toggle_state_btn.config(state=state)
        self.web_btn.config(state=state)

        if has_sel:
            is_open = self.selected_issue.get("state", "OPEN").upper() == "OPEN"
            self.toggle_state_btn.config(text="Close Issue" if is_open else "Reopen Issue")

    def _view_details(self) -> None:
        if not self.selected_issue:
            return
        num = self.selected_issue.get("number")
        IssueDetailsDialog(self.winfo_toplevel(), self.current_repo, num, self.gh_manager, on_updated=self.refresh)

    def _new_issue(self) -> None:
        CreateIssueDialog(self.winfo_toplevel(), self.current_repo, self.gh_manager, on_created=lambda r: self.refresh())

    def _toggle_state(self) -> None:
        if not self.selected_issue:
            return
        num = self.selected_issue.get("number")
        is_open = self.selected_issue.get("state", "OPEN").upper() == "OPEN"

        if is_open:
            if self.config.get("confirmations", "confirm_close_issue", True):
                if not messagebox.askyesno("Confirm Close", f"Close issue #{num}?", parent=self.winfo_toplevel()):
                    return
            try:
                self.gh_manager.issues.close_issue(self.current_repo, num)
                self.set_status(f"Closed issue #{num}")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.winfo_toplevel())
        else:
            try:
                self.gh_manager.issues.reopen_issue(self.current_repo, num)
                self.set_status(f"Reopened issue #{num}")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.winfo_toplevel())

    def _open_in_browser(self) -> None:
        if not self.selected_issue:
            return
        url = self.selected_issue.get("url") or f"https://github.com/{self.current_repo}/issues/{self.selected_issue.get('number')}"
        self.gh_manager.open_in_browser(url)

    def _copy_number(self) -> None:
        if self.selected_issue:
            self.clipboard_clear()
            self.clipboard_append(str(self.selected_issue.get("number", "")))

    def _copy_title(self) -> None:
        if self.selected_issue:
            self.clipboard_clear()
            self.clipboard_append(self.selected_issue.get("title", ""))

    def _copy_url(self) -> None:
        if self.selected_issue:
            url = self.selected_issue.get("url") or f"https://github.com/{self.current_repo}/issues/{self.selected_issue.get('number')}"
            self.clipboard_clear()
            self.clipboard_append(url)
