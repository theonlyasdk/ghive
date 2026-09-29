"""Gists tab for browsing and managing GitHub code snippets."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import CloneRepoDialog, CreateGistDialog, GistDetailsDialog
from ui.widgets import EmptyState, LoadingOverlay, SearchEntry


class GistsTab(ttk.Frame):
    """Tab for listing, previewing, creating, and deleting GitHub gists."""

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

        self.gists: List[Dict[str, Any]] = []
        self.filtered_gists: List[Dict[str, Any]] = []
        self.selected_gist: Optional[Dict[str, Any]] = None
        self._sort_col: str = "Updated"
        self._sort_reverse: bool = True

        self._create_ui()

    def _create_ui(self) -> None:
        # Top toolbar
        toolbar = ttk.Frame(self, padding=(6, 6))
        toolbar.pack(fill=tk.X)

        self.search_entry = SearchEntry(toolbar, placeholder="Search gists...", on_search=self._filter_list, width=28)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.vis_var = tk.StringVar(value="All")
        vis_cb = ttk.Combobox(toolbar, textvariable=self.vis_var, values=["All", "Public", "Secret"], state="readonly", width=8)
        vis_cb.pack(side=tk.LEFT, padx=(0, 8))
        vis_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side=tk.RIGHT)

        # Main Content Area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("ID", "Description", "Files", "Visibility", "Updated")
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        self.tree.column("ID", width=110, anchor="center")
        self.tree.column("Description", width=340)
        self.tree.column("Files", width=140)
        self.tree.column("Visibility", width=90, anchor="center")
        self.tree.column("Updated", width=130, anchor="center")

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
            title="No Gists Found",
            instructions=[
                "No gists found under your account matching the current filter.",
                "Click 'New Gist...' below to create a code snippet.",
            ],
            action_text="Create Gist",
            action_command=self._new_gist,
        )

        # Bottom Button Bar
        self.btn_bar = ttk.Frame(self, padding=(6, 6))
        self.btn_bar.pack(fill=tk.X)

        self.new_btn = ttk.Button(self.btn_bar, text="New Gist...", command=self._new_gist)
        self.new_btn.pack(side=tk.LEFT, padx=2)

        self.details_btn = ttk.Button(self.btn_bar, text="View Details", command=self._view_details, state=tk.DISABLED)
        self.details_btn.pack(side=tk.LEFT, padx=2)

        self.clone_btn = ttk.Button(self.btn_bar, text="Clone Gist...", command=self._clone_gist, state=tk.DISABLED)
        self.clone_btn.pack(side=tk.LEFT, padx=2)

        self.web_btn = ttk.Button(self.btn_bar, text="Open in Browser", command=self._open_in_browser, state=tk.DISABLED)
        self.web_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(self.btn_bar, text="Delete Gist...", command=self._delete_gist, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.RIGHT, padx=2)

        self.loading_overlay = LoadingOverlay(self)
        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

    def _create_context_menu(self) -> None:
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self._view_details)
        self.context_menu.add_command(label="Clone Gist Locally...", command=self._clone_gist)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open in Browser", command=self._open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Gist ID", command=self._copy_id)
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Gist...", command=self._delete_gist)

        def show_menu(event):
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self._on_select()
                self.context_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", show_menu)

    def refresh(self) -> None:
        """Fetch user gists asynchronously."""
        self.set_status("Fetching gists...")
        self.refresh_btn.config(state=tk.DISABLED)

        self.content_frame.pack_forget()
        self.btn_bar.pack_forget()
        self.loading_overlay.show()

        vis_choice = self.vis_var.get().lower()
        vis_param = vis_choice if vis_choice in ("public", "secret") else None
        limit = self.config.get("general", "default_limit", 30)

        def _task():
            return self.gh_manager.gists.list_gists(limit=limit, visibility=vis_param)

        def _on_success(data):
            self.gists = data
            self._filter_list(self.search_entry.get_query())
            self.set_status(f"Loaded {len(data)} gists")

        def _on_error(exc):
            self.set_status(f"Error fetching gists: {exc}")
            messagebox.showerror("Error", f"Failed to fetch gists:\n{exc}", parent=self.winfo_toplevel())

        def _on_complete():
            self.loading_overlay.hide()
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
            self.btn_bar.pack(fill=tk.X)
            self.refresh_btn.config(state=tk.NORMAL)

        self.async_runner.run(_task, on_success=_on_success, on_error=_on_error, on_complete=_on_complete)

    def _filter_list(self, query: str = "") -> None:
        q = query.strip().lower()
        if not q:
            self.filtered_gists = list(self.gists)
        else:
            self.filtered_gists = [
                g for g in self.gists
                if q in g.get("id", "").lower()
                or q in g.get("description", "").lower()
                or any(q in f.lower() for f in g.get("files", []))
            ]

        self._populate_tree()

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.filtered_gists:
            self.tree.pack_forget()
            self.empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_button_states()
            return

        self.empty_state.pack_forget()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for gist in self.filtered_gists:
            gid = gist.get("id", "")[:12] + "..." if len(gist.get("id", "")) > 12 else gist.get("id", "")
            desc = gist.get("description", "")
            files_str = ", ".join(gist.get("files", []))
            vis = "Public" if gist.get("public") else "Secret"
            updated = gist.get("updated_at", "").replace("T", " ").replace("Z", "")[:16]

            self.tree.insert("", tk.END, values=(gid, desc, files_str, vis, updated))

        self._update_button_states()

    def _sort_by_column(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_map = {
            "ID": lambda g: g.get("id", ""),
            "Description": lambda g: g.get("description", "").lower(),
            "Files": lambda g: g.get("file_count", 0),
            "Visibility": lambda g: g.get("public", False),
            "Updated": lambda g: g.get("updated_at", ""),
        }

        key_func = key_map.get(col, lambda g: "")
        self.filtered_gists.sort(key=key_func, reverse=self._sort_reverse)
        self._populate_tree()

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_gist = None
            self._update_button_states()
            return

        item = self.tree.item(selection[0])
        gid_prefix = item["values"][0].replace("...", "")
        matched = next((g for g in self.gists if g.get("id", "").startswith(gid_prefix)), None)
        self.selected_gist = matched
        self._update_button_states()

    def _update_button_states(self) -> None:
        has_sel = self.selected_gist is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.details_btn.config(state=state)
        self.clone_btn.config(state=state)
        self.web_btn.config(state=state)
        self.delete_btn.config(state=state)

    def _view_details(self) -> None:
        if not self.selected_gist:
            return
        GistDetailsDialog(
            self.winfo_toplevel(),
            self.selected_gist,
            self.gh_manager,
            on_clone_requested=lambda gid: self._clone_gist(gid),
        )

    def _new_gist(self) -> None:
        CreateGistDialog(self.winfo_toplevel(), self.gh_manager, on_created=lambda out: self.refresh())

    def _clone_gist(self, gist_id: Optional[str] = None) -> None:
        target_id = gist_id or (self.selected_gist.get("id") if self.selected_gist else "")
        if not target_id:
            return
        CloneRepoDialog(
            self.winfo_toplevel(),
            self.gh_manager,
            default_repo=target_id,
            on_cloned=lambda repo, path: self.set_status(f"Cloned gist {repo} to {path}"),
        )

    def _delete_gist(self) -> None:
        if not self.selected_gist:
            return
        gid = self.selected_gist.get("id", "")
        if self.config.get("confirmations", "confirm_delete_gist", True):
            prompt = f"Are you sure you want to permanently delete gist '{gid}'?\nThis cannot be undone!"
            if not messagebox.askyesno("Confirm Delete Gist (Step 1/2)", prompt, parent=self.winfo_toplevel(), icon=messagebox.WARNING):
                return

            verify = simpledialog.askstring(
                "Confirm Delete Gist (Step 2/2)",
                "Double Protection: Please type 'DELETE' to confirm deletion:",
                parent=self.winfo_toplevel(),
            )
            if verify != "DELETE":
                messagebox.showinfo("Deletion Cancelled", "Confirmation phrase did not match. Deletion aborted.", parent=self.winfo_toplevel())
                return

        self.set_status(f"Deleting gist {gid}...")
        try:
            self.gh_manager.gists.delete_gist(gid)
            messagebox.showinfo("Success", f"Gist '{gid}' deleted.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Delete Failed", str(e), parent=self.winfo_toplevel())

    def _open_in_browser(self) -> None:
        if not self.selected_gist:
            return
        url = self.selected_gist.get("url") or f"https://gist.github.com/{self.selected_gist.get('id')}"
        self.gh_manager.open_in_browser(url)

    def _copy_id(self) -> None:
        if self.selected_gist:
            self.clipboard_clear()
            self.clipboard_append(self.selected_gist.get("id", ""))

    def _copy_url(self) -> None:
        if self.selected_gist:
            url = self.selected_gist.get("url") or f"https://gist.github.com/{self.selected_gist.get('id')}"
            self.clipboard_clear()
            self.clipboard_append(url)
