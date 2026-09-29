"""Repositories tab for browsing and managing GitHub repositories."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import CloneRepoDialog, CreateRepoDialog, RepoDetailsDialog
from ui.widgets import EmptyState, LoadingOverlay, SearchEntry


class ReposTab(ttk.Frame):
    """Tab for listing, searching, creating, and cloning repositories."""

    def __init__(
        self,
        parent: tk.Widget,
        gh_manager: GHManager,
        async_runner: AsyncRunner,
        set_status: Callable[[str], None],
        on_active_repo_changed: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self.gh_manager = gh_manager
        self.async_runner = async_runner
        self.set_status = set_status
        self.on_active_repo_changed = on_active_repo_changed
        self.config = ConfigManager()

        self.repos: List[Dict[str, Any]] = []
        self.filtered_repos: List[Dict[str, Any]] = []
        self.selected_repo: Optional[Dict[str, Any]] = None
        self._sort_col: str = "Updated"
        self._sort_reverse: bool = True

        self._create_ui()

    def _create_ui(self) -> None:
        # Top toolbar
        toolbar = ttk.Frame(self, padding=(6, 6))
        toolbar.pack(fill=tk.X)

        self.search_entry = SearchEntry(toolbar, placeholder="Search repositories...", on_search=self._filter_list, width=28)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.vis_var = tk.StringVar(value="All")
        vis_cb = ttk.Combobox(toolbar, textvariable=self.vis_var, values=["All", "Public", "Private", "Forks", "Sources"], state="readonly", width=9)
        vis_cb.pack(side=tk.LEFT, padx=(0, 8))
        vis_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(toolbar, text="Limit:").pack(side=tk.LEFT, padx=(0, 4))
        self.limit_var = tk.StringVar(value=str(self.config.get("general", "default_limit", 30)))
        limit_cb = ttk.Combobox(toolbar, textvariable=self.limit_var, values=["15", "30", "50", "100"], state="readonly", width=6)
        limit_cb.pack(side=tk.LEFT, padx=(0, 8))
        limit_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side=tk.RIGHT)

        # Main content area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("Name", "Visibility", "Stars", "Forks", "Updated")
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        self.tree.column("Name", width=340)
        self.tree.column("Visibility", width=90, anchor="center")
        self.tree.column("Stars", width=70, anchor="center")
        self.tree.column("Forks", width=70, anchor="center")
        self.tree.column("Updated", width=140, anchor="center")

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
            title="No Repositories Found",
            instructions=[
                "No repositories match your current filter, or you haven't created any yet.",
                "Click 'New Repo...' below to create a new repository.",
            ],
            action_text="Create Repository",
            action_command=self._new_repo,
        )

        # Bottom Button Bar
        self.btn_bar = ttk.Frame(self, padding=(6, 6))
        self.btn_bar.pack(fill=tk.X)

        self.new_btn = ttk.Button(self.btn_bar, text="New Repo...", command=self._new_repo)
        self.new_btn.pack(side=tk.LEFT, padx=2)

        self.clone_btn = ttk.Button(self.btn_bar, text="Clone...", command=self._clone_repo)
        self.clone_btn.pack(side=tk.LEFT, padx=2)

        self.details_btn = ttk.Button(self.btn_bar, text="View Details", command=self._view_details, state=tk.DISABLED)
        self.details_btn.pack(side=tk.LEFT, padx=2)

        self.web_btn = ttk.Button(self.btn_bar, text="Open in Browser", command=self._open_in_browser, state=tk.DISABLED)
        self.web_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(self.btn_bar, text="Delete...", command=self._delete_repo, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.RIGHT, padx=2)

        self.loading_overlay = LoadingOverlay(self)
        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

    def _create_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self._view_details)
        self.context_menu.add_command(label="Open in Browser", command=self._open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clone Locally...", command=self._clone_repo)
        self.context_menu.add_command(label="Sync Fork", command=self._sync_fork)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Full Name", command=self._copy_name)
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Repository...", command=self._delete_repo)

        def show_menu(event):
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self._on_select()
                self.context_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", show_menu)

    def refresh(self) -> None:
        """Fetch repositories asynchronously."""
        self.set_status("Fetching repositories...")
        self.refresh_btn.config(state=tk.DISABLED)

        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 30

        vis_choice = self.vis_var.get().lower()
        vis_param = None
        fork_param = None
        if vis_choice in ("public", "private"):
            vis_param = vis_choice
        elif vis_choice == "forks":
            fork_param = True
        elif vis_choice == "sources":
            fork_param = False

        def _task():
            return self.gh_manager.repos.list_repos(limit=limit, visibility=vis_param, fork=fork_param)

        def _on_success(data):
            self.repos = data
            self._filter_list(self.search_entry.get_query())
            self.set_status(f"Loaded {len(data)} repositories")

        def _on_error(exc):
            self.set_status(f"Error fetching repositories: {exc}")
            messagebox.showerror("Error", f"Failed to fetch repositories:\n{exc}", parent=self.winfo_toplevel())

        def _on_complete():
            self.loading_overlay.hide()
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
            self.btn_bar.pack(fill=tk.X)
            self.refresh_btn.config(state=tk.NORMAL)

        self.async_runner.run(_task, on_success=_on_success, on_error=_on_error, on_complete=_on_complete)

    def _filter_list(self, query: str = "") -> None:
        q = query.strip().lower()
        if not q:
            self.filtered_repos = list(self.repos)
        else:
            self.filtered_repos = [
                r for r in self.repos
                if q in r.get("nameWithOwner", "").lower() or q in (r.get("description") or "").lower()
            ]

        self._populate_tree()

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.filtered_repos:
            self.tree.pack_forget()
            self.empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_button_states()
            return

        self.empty_state.pack_forget()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for repo in self.filtered_repos:
            full_name = repo.get("nameWithOwner") or repo.get("name", "Unknown")
            is_priv = repo.get("isPrivate", False)
            is_fork = repo.get("isFork", False)
            vis = "Private" if is_priv else "Public"
            if is_fork:
                vis += " (Fork)"
            stars = repo.get("stargazerCount", 0)
            forks = repo.get("forkCount", 0)
            updated = repo.get("updatedAt", "").replace("T", " ").replace("Z", "")[:16]

            self.tree.insert("", tk.END, values=(full_name, vis, stars, forks, updated))

        self._update_button_states()

    def _sort_by_column(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_map = {
            "Name": lambda r: r.get("nameWithOwner", "").lower(),
            "Visibility": lambda r: r.get("isPrivate", False),
            "Stars": lambda r: r.get("stargazerCount", 0),
            "Forks": lambda r: r.get("forkCount", 0),
            "Updated": lambda r: r.get("updatedAt", ""),
        }

        key_func = key_map.get(col, lambda r: "")
        self.filtered_repos.sort(key=key_func, reverse=self._sort_reverse)
        self._populate_tree()

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_repo = None
            self._update_button_states()
            return

        item = self.tree.item(selection[0])
        full_name = item["values"][0]

        matched = next((r for r in self.repos if r.get("nameWithOwner") == full_name or r.get("name") == full_name), None)
        self.selected_repo = matched or {"nameWithOwner": full_name, "name": full_name}

        self._update_button_states()
        if self.on_active_repo_changed and full_name:
            self.on_active_repo_changed(full_name)

    def _update_button_states(self) -> None:
        has_sel = self.selected_repo is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.details_btn.config(state=state)
        self.web_btn.config(state=state)
        self.delete_btn.config(state=state)

    def _view_details(self) -> None:
        if not self.selected_repo:
            return
        RepoDetailsDialog(
            self.winfo_toplevel(),
            self.selected_repo,
            self.gh_manager,
            on_clone_requested=lambda name: self._clone_repo(name),
        )

    def _new_repo(self) -> None:
        CreateRepoDialog(self.winfo_toplevel(), self.gh_manager, on_created=lambda name: self.refresh())

    def _clone_repo(self, repo_name: Optional[str] = None) -> None:
        target = repo_name or (self.selected_repo.get("nameWithOwner") if self.selected_repo else "")
        CloneRepoDialog(
            self.winfo_toplevel(),
            self.gh_manager,
            default_repo=target or "",
            on_cloned=lambda repo, path: self.set_status(f"Cloned {repo} to {path}"),
        )

    def _delete_repo(self) -> None:
        if not self.selected_repo:
            return
        full_name = self.selected_repo.get("nameWithOwner") or self.selected_repo.get("name", "")
        if self.config.get("confirmations", "confirm_delete_repo", True):
            prompt = f"Are you sure you want to PERMANENTLY DELETE '{full_name}'?\nThis will delete all code, issues, and PRs. This cannot be undone!"
            if not messagebox.askyesno("Confirm Delete Repository (Step 1/2)", prompt, parent=self.winfo_toplevel(), icon=messagebox.WARNING):
                return

            verify = simpledialog.askstring(
                "Confirm Delete Repository (Step 2/2)",
                f"Double Protection: Please type '{full_name}' to permanently delete:",
                parent=self.winfo_toplevel(),
            )
            if verify != full_name:
                messagebox.showinfo("Deletion Cancelled", "Repository name did not match. Deletion aborted.", parent=self.winfo_toplevel())
                return

        self.set_status(f"Deleting repository {full_name}...")
        try:
            self.gh_manager.repos.delete_repo(full_name)
            messagebox.showinfo("Success", f"Repository '{full_name}' deleted.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete repository:\n{e}", parent=self.winfo_toplevel())

    def _sync_fork(self) -> None:
        if not self.selected_repo:
            return
        full_name = self.selected_repo.get("nameWithOwner") or self.selected_repo.get("name", "")
        self.set_status(f"Syncing fork {full_name}...")
        try:
            out = self.gh_manager.repos.sync_repo(full_name)
            messagebox.showinfo("Fork Synced", out or "Repository is already up to date.", parent=self.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Sync Failed", str(e), parent=self.winfo_toplevel())

    def _open_in_browser(self) -> None:
        if not self.selected_repo:
            return
        url = self.selected_repo.get("url") or f"https://github.com/{self.selected_repo.get('nameWithOwner', '')}"
        self.gh_manager.open_in_browser(url)

    def _copy_name(self) -> None:
        if self.selected_repo:
            name = self.selected_repo.get("nameWithOwner") or self.selected_repo.get("name", "")
            self.clipboard_clear()
            self.clipboard_append(name)

    def _copy_url(self) -> None:
        if self.selected_repo:
            url = self.selected_repo.get("url") or f"https://github.com/{self.selected_repo.get('nameWithOwner', '')}"
            self.clipboard_clear()
            self.clipboard_append(url)
