"""Workflow runs tab for inspecting and managing GitHub Actions CI/CD."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import RunDetailsDialog
from ui.widgets import EmptyState, LoadingOverlay


class RunsTab(ttk.Frame):
    """Tab for listing, inspecting logs, rerunning, and cancelling GitHub Actions workflow runs."""

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
        self.runs: List[Dict[str, Any]] = []
        self.selected_run: Optional[Dict[str, Any]] = None
        self._sort_col: str = "Created"
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

        ttk.Label(toolbar, text="Status:").pack(side=tk.LEFT, padx=(0, 4))
        self.status_filter_var = tk.StringVar(value="all")
        status_cb = ttk.Combobox(toolbar, textvariable=self.status_filter_var, values=["all", "queued", "in_progress", "completed"], state="readonly", width=12)
        status_cb.pack(side=tk.LEFT, padx=(0, 8))
        status_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side=tk.RIGHT)

        # Main Content Area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("Run ID", "Workflow", "Event", "Branch", "Conclusion", "Created")
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        self.tree.column("Run ID", width=100, anchor="center")
        self.tree.column("Workflow", width=260)
        self.tree.column("Event", width=90, anchor="center")
        self.tree.column("Branch", width=120, anchor="center")
        self.tree.column("Conclusion", width=100, anchor="center")
        self.tree.column("Created", width=130, anchor="center")

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
            title="No Workflow Runs Found",
            instructions=[
                "Select a repository above to view its GitHub Actions execution runs.",
                "Ensure GitHub Actions is enabled on the repository.",
            ],
            action_text="Refresh Runs",
            action_command=self.refresh,
        )

        # Bottom Button Bar
        self.btn_bar = ttk.Frame(self, padding=(6, 6))
        self.btn_bar.pack(fill=tk.X)

        self.details_btn = ttk.Button(self.btn_bar, text="View Logs & Details", command=self._view_details, state=tk.DISABLED)
        self.details_btn.pack(side=tk.LEFT, padx=2)

        self.rerun_btn = ttk.Button(self.btn_bar, text="Rerun Workflow", command=self._rerun_run, state=tk.DISABLED)
        self.rerun_btn.pack(side=tk.LEFT, padx=2)

        self.cancel_btn = ttk.Button(self.btn_bar, text="Cancel Run", command=self._cancel_run, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=2)

        self.web_btn = ttk.Button(self.btn_bar, text="Open in Browser", command=self._open_in_browser, state=tk.DISABLED)
        self.web_btn.pack(side=tk.LEFT, padx=2)

        self.loading_overlay = LoadingOverlay(self)
        if self.config.get("general", "active_repo", ""):
            self.content_frame.pack_forget()
            self.btn_bar.pack_forget()
            self.loading_overlay.show()

    def _create_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Logs & Details", command=self._view_details)
        self.context_menu.add_command(label="Rerun Workflow", command=self._rerun_run)
        self.context_menu.add_command(label="Cancel Run", command=self._cancel_run)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open in Browser", command=self._open_in_browser)
        self.context_menu.add_command(label="Copy Run ID", command=self._copy_id)

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
        """Fetch workflow runs for current repository asynchronously."""
        repo = self.repo_var.get().strip()
        if not repo:
            self.runs = []
            self._populate_tree()
            return

        self.current_repo = repo
        status_filter = self.status_filter_var.get()
        status_val = status_filter if status_filter != "all" else None

        self.set_status(f"Fetching workflow runs for {repo}...")
        self.refresh_btn.config(state=tk.DISABLED)

        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

        limit = self.config.get("general", "default_limit", 30)

        def _task():
            return self.gh_manager.runs.list_runs(repo=repo, limit=limit, status=status_val)

        def _on_success(data):
            self.runs = data
            self._populate_tree()
            self.set_status(f"Loaded {len(data)} workflow runs for {repo}")

        def _on_error(exc):
            self.set_status(f"Error fetching workflow runs: {exc}")
            messagebox.showerror("Error", f"Failed to fetch workflow runs:\n{exc}", parent=self.winfo_toplevel())

        def _on_complete():
            self.loading_overlay.hide()
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
            self.btn_bar.pack(fill=tk.X)
            self.refresh_btn.config(state=tk.NORMAL)

        self.async_runner.run(_task, on_success=_on_success, on_error=_on_error, on_complete=_on_complete)

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.runs:
            self.tree.pack_forget()
            self.empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_button_states()
            return

        self.empty_state.pack_forget()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for run in self.runs:
            run_id = str(run.get("databaseId", ""))
            wf_name = run.get("workflowName") or run.get("name", "Unknown")
            event = run.get("event", "")
            branch = run.get("headBranch", "")
            status = run.get("status", "").lower()
            conclusion = run.get("conclusion") or status
            created = run.get("createdAt", "").replace("T", " ").replace("Z", "")[:16]

            self.tree.insert("", tk.END, values=(run_id, wf_name, event, branch, conclusion, created))

        self._update_button_states()

    def _sort_by_column(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_map = {
            "Run ID": lambda r: r.get("databaseId", 0),
            "Workflow": lambda r: (r.get("workflowName") or r.get("name", "")).lower(),
            "Event": lambda r: r.get("event", "").lower(),
            "Branch": lambda r: r.get("headBranch", "").lower(),
            "Conclusion": lambda r: (r.get("conclusion") or r.get("status", "")).lower(),
            "Created": lambda r: r.get("createdAt", ""),
        }

        key_func = key_map.get(col, lambda r: "")
        self.runs.sort(key=key_func, reverse=self._sort_reverse)
        self._populate_tree()

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_run = None
            self._update_button_states()
            return

        item = self.tree.item(selection[0])
        run_id = str(item["values"][0])
        matched = next((r for r in self.runs if str(r.get("databaseId")) == run_id), None)
        self.selected_run = matched
        self._update_button_states()

    def _update_button_states(self) -> None:
        has_sel = self.selected_run is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.details_btn.config(state=state)
        self.rerun_btn.config(state=state)
        self.web_btn.config(state=state)

        if has_sel:
            is_in_progress = self.selected_run.get("status", "").lower() in ("in_progress", "queued")
            self.cancel_btn.config(state=tk.NORMAL if is_in_progress else tk.DISABLED)
        else:
            self.cancel_btn.config(state=tk.DISABLED)

    def _view_details(self) -> None:
        if not self.selected_run:
            return
        RunDetailsDialog(self.winfo_toplevel(), self.current_repo, self.selected_run, self.gh_manager, on_updated=self.refresh)

    def _rerun_run(self) -> None:
        if not self.selected_run:
            return
        run_id = self.selected_run.get("databaseId")
        self.set_status(f"Rerunning workflow #{run_id}...")
        try:
            self.gh_manager.runs.rerun(self.current_repo, run_id)
            messagebox.showinfo("Success", f"Workflow run #{run_id} restarted.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rerun workflow:\n{e}", parent=self.winfo_toplevel())

    def _cancel_run(self) -> None:
        if not self.selected_run:
            return
        run_id = self.selected_run.get("databaseId")
        if not messagebox.askyesno("Confirm Cancel", f"Cancel in-progress workflow run #{run_id}?", parent=self.winfo_toplevel()):
            return

        self.set_status(f"Cancelling workflow #{run_id}...")
        try:
            self.gh_manager.runs.cancel(self.current_repo, run_id)
            messagebox.showinfo("Success", f"Workflow run #{run_id} cancelled.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to cancel workflow:\n{e}", parent=self.winfo_toplevel())

    def _open_in_browser(self) -> None:
        if not self.selected_run:
            return
        url = self.selected_run.get("url") or f"https://github.com/{self.current_repo}/actions/runs/{self.selected_run.get('databaseId')}"
        self.gh_manager.open_in_browser(url)

    def _copy_id(self) -> None:
        if self.selected_run:
            self.clipboard_clear()
            self.clipboard_append(str(self.selected_run.get("databaseId", "")))
