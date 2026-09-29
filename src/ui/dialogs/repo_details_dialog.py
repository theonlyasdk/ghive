"""Repository details dialog with split Details and Releases tabs."""

import platform
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional

from core import GHManager
from ui.dialogs.create_release_dialog import CreateReleaseDialog
from ui.dialogs.release_management_dialog import ReleaseManagementDialog
from ui.widgets import EmptyState, LoadingOverlay


class RepoDetailsDialog:
    """Dialog showing repository information and releases split across tabs."""

    def __init__(
        self,
        parent: tk.Widget,
        repo_data: Dict[str, Any],
        gh_manager: GHManager,
        on_clone_requested: Optional[Callable[[str], None]] = None,
    ):
        self.parent = parent
        self.repo = repo_data
        self.gh_manager = gh_manager
        self.on_clone_requested = on_clone_requested

        self.full_name = self.repo.get("nameWithOwner") or self.repo.get("name", "Repository")
        self.releases: List[Dict[str, Any]] = []

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Repository Details - {self.full_name}")
        self.dialog.geometry("700x580")
        self.dialog.minsize(620, 500)
        self.dialog.transient(parent)

        self._create_menu()
        self._create_visibility_menu()
        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 700
            dh = 580
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

        # Load releases initially
        self._refresh_releases()

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.dialog)
        self.dialog.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open in Browser", command=self._open_web)
        if self.on_clone_requested:
            file_menu.add_command(label="Clone Repository Locally...", command=self._trigger_clone)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.dialog.destroy)

        # Releases Menu
        rel_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Releases", menu=rel_menu)
        rel_menu.add_command(label="New Release...", command=self._new_release)
        rel_menu.add_command(label="Manage Selected Release", command=self._manage_selected_release)
        rel_menu.add_separator()
        rel_menu.add_command(label="Refresh Releases", command=self._refresh_releases)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Releases", command=self._refresh_releases)

    def _create_widgets(self) -> None:
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Tab 1: Details
        details_frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(details_frame, text="Details")
        self._populate_details_tab(details_frame)

        # Tab 2: Releases
        releases_frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(releases_frame, text="Releases")
        self._populate_releases_tab(releases_frame)

    def _populate_details_tab(self, parent: ttk.Frame) -> None:
        is_private = self.repo.get("isPrivate", False)
        is_fork = self.repo.get("isFork", False)

        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 6))

        system = platform.system().lower()
        light_font = "Segoe UI Light" if system == "windows" else ("Helvetica Neue Light" if system == "darwin" else "Ubuntu Light")
        title_lbl = tk.Label(header_frame, text=self.full_name, font=(light_font, 20), fg="#0969da", anchor=tk.W)
        title_lbl.pack(side=tk.LEFT)

        vis_text = "Private" if is_private else "Public"
        if is_fork:
            vis_text += " (Fork)"
        self.badge_lbl = tk.Label(
            header_frame,
            text=f"{vis_text} ▾",
            font=("Segoe UI", 9, "bold"),
            fg="#cf222e" if is_private else "#1a7f37",
            cursor="hand2",
        )
        self.badge_lbl.pack(side=tk.RIGHT)
        self.badge_lbl.bind("<Button-1>", self._show_visibility_menu)

        desc_text = self.repo.get("description") or "(No description provided)"
        desc_lbl = tk.Label(parent, text=desc_text, font=("Segoe UI", 9), fg="#24292f", wraplength=640, justify=tk.LEFT, anchor=tk.W)
        desc_lbl.pack(fill=tk.X, pady=(0, 10))

        stats_box = ttk.LabelFrame(parent, text="Repository Statistics", padding=10)
        stats_box.pack(fill=tk.X, pady=(0, 10))

        stars = self.repo.get("stargazerCount", 0)
        forks = self.repo.get("forkCount", 0)
        branch = self.repo.get("defaultBranchRef", {}).get("name", "main") if isinstance(self.repo.get("defaultBranchRef"), dict) else "main"

        license_info = self.repo.get("licenseInfo")
        license_name = license_info.get("name") if isinstance(license_info, dict) else (license_info or "None")

        updated = self.repo.get("updatedAt", "").replace("T", " ").replace("Z", "")

        ttk.Label(stats_box, text=f"Stars: ⭐ {stars}").grid(row=0, column=0, sticky=tk.W, padx=8, pady=3)
        ttk.Label(stats_box, text=f"Forks: 🍴 {forks}").grid(row=0, column=1, sticky=tk.W, padx=8, pady=3)
        ttk.Label(stats_box, text=f"Default Branch: {branch}").grid(row=1, column=0, sticky=tk.W, padx=8, pady=3)
        ttk.Label(stats_box, text=f"License: {license_name}").grid(row=1, column=1, sticky=tk.W, padx=8, pady=3)
        ttk.Label(stats_box, text=f"Last Updated: {updated}").grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=8, pady=3)

        langs = self.repo.get("languages", [])
        if langs and isinstance(langs, list):
            lang_names = [item["node"]["name"] for item in langs if isinstance(item, dict) and "node" in item]
            if lang_names:
                lang_box = ttk.LabelFrame(parent, text="Languages", padding=8)
                lang_box.pack(fill=tk.X, pady=(0, 10))
                tk.Label(lang_box, text=", ".join(lang_names[:8]), font=("Segoe UI", 9), anchor=tk.W).pack(fill=tk.X)

        clone_box = ttk.LabelFrame(parent, text="Clone URLs", padding=10)
        clone_box.pack(fill=tk.X, pady=(0, 12))

        web_url = self.repo.get("url") or f"https://github.com/{self.full_name}"
        ssh_url = self.repo.get("sshUrl") or f"git@github.com:{self.full_name}.git"

        self._create_copy_row(clone_box, "HTTPS:", web_url + ".git")
        self._create_copy_row(clone_box, "SSH:", ssh_url)

        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Open in Browser", command=self._open_web, width=14).pack(side=tk.RIGHT, padx=6)
        if self.on_clone_requested:
            ttk.Button(btn_bar, text="Clone Locally...", command=self._trigger_clone, width=14).pack(side=tk.LEFT)

    def _populate_releases_tab(self, parent: ttk.Frame) -> None:
        self.rel_parent = parent

        # Releases top toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        self.rel_refresh_btn = ttk.Button(toolbar, text="Refresh", command=self._refresh_releases)
        self.rel_refresh_btn.pack(side=tk.RIGHT)

        ttk.Button(toolbar, text="New Release...", command=self._new_release).pack(side=tk.LEFT)

        # Releases content area
        self.rel_content_frame = ttk.Frame(parent)
        self.rel_content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("Tag", "Title", "Type", "Published")
        self.rel_tree = ttk.Treeview(self.rel_content_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.rel_tree.heading(c, text=c)

        self.rel_tree.column("Tag", width=120)
        self.rel_tree.column("Title", width=240)
        self.rel_tree.column("Type", width=110, anchor="center")
        self.rel_tree.column("Published", width=140, anchor="center")

        scroll = ttk.Scrollbar(self.rel_content_frame, orient=tk.VERTICAL, command=self.rel_tree.yview)
        self.rel_tree.configure(yscrollcommand=scroll.set)

        self.rel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.rel_tree.bind("<<TreeviewSelect>>", lambda e: self._update_rel_buttons())
        self.rel_tree.bind("<Double-1>", lambda e: self._manage_selected_release())
        self.rel_tree.bind("<Return>", lambda e: self._manage_selected_release())

        self.rel_empty_state = EmptyState(
            self.rel_content_frame,
            title="No Releases Found",
            instructions=[
                "There are no releases published for this repository yet.",
                "Click 'New Release...' to create your first release.",
            ],
            action_text="Create Release",
            action_command=self._new_release,
        )

        self.rel_loading = LoadingOverlay(self.rel_content_frame)

        # Bottom Button Bar for Releases
        self.rel_btn_bar = ttk.Frame(parent)
        self.rel_btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.manage_rel_btn = ttk.Button(self.rel_btn_bar, text="Manage Release...", command=self._manage_selected_release, state=tk.DISABLED)
        self.manage_rel_btn.pack(side=tk.LEFT, padx=2)

        self.download_assets_btn = ttk.Button(self.rel_btn_bar, text="Download Assets...", command=self._download_release_assets, state=tk.DISABLED)
        self.download_assets_btn.pack(side=tk.LEFT, padx=2)

        self.open_rel_web_btn = ttk.Button(self.rel_btn_bar, text="Open in Browser", command=self._open_selected_release_web, state=tk.DISABLED)
        self.open_rel_web_btn.pack(side=tk.LEFT, padx=2)

        self.delete_rel_btn = ttk.Button(self.rel_btn_bar, text="Delete Release...", command=self._delete_selected_release, state=tk.DISABLED)
        self.delete_rel_btn.pack(side=tk.RIGHT, padx=2)

    def _refresh_releases(self) -> None:
        self.rel_tree.pack_forget()
        self.rel_empty_state.pack_forget()
        self.rel_loading.show()
        self.rel_refresh_btn.config(state=tk.DISABLED)

        def _task():
            return self.gh_manager.releases.list_releases(self.full_name)

        def _on_success(data):
            self.releases = data
            self.rel_loading.hide()
            self._populate_releases_tree()
            self.rel_refresh_btn.config(state=tk.NORMAL)

        def _on_error(exc):
            self.rel_loading.hide()
            self.rel_refresh_btn.config(state=tk.NORMAL)
            self._populate_releases_tree()
            messagebox.showerror("Error", f"Failed to fetch releases:\n{exc}", parent=self.dialog)

        def _worker():
            try:
                res = _task()
                self.dialog.after(0, lambda r=res: _on_success(r))
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: _on_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_releases_tree(self) -> None:
        for item in self.rel_tree.get_children():
            self.rel_tree.delete(item)

        if not self.releases:
            self.rel_tree.pack_forget()
            self.rel_empty_state.pack(fill=tk.BOTH, expand=True)
            self._update_rel_buttons()
            return

        self.rel_empty_state.pack_forget()
        self.rel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for rel in self.releases:
            tag = rel.get("tagName", "Unknown")
            name = rel.get("name") or tag
            is_latest = rel.get("isLatest", False)
            is_draft = rel.get("isDraft", False)
            is_prerel = rel.get("isPrerelease", False)

            if is_draft:
                rel_type = "Draft"
            elif is_prerel:
                rel_type = "Pre-release"
            elif is_latest:
                rel_type = "Latest"
            else:
                rel_type = "Release"

            pub = (rel.get("publishedAt") or rel.get("createdAt") or "").replace("T", " ").replace("Z", "")[:16]
            self.rel_tree.insert("", tk.END, values=(tag, name, rel_type, pub))

        self._update_rel_buttons()

    def _get_selected_release(self) -> Optional[Dict[str, Any]]:
        sel = self.rel_tree.selection()
        if not sel:
            return None
        idx = self.rel_tree.index(sel[0])
        if 0 <= idx < len(self.releases):
            return self.releases[idx]
        return None

    def _update_rel_buttons(self) -> None:
        has_sel = self._get_selected_release() is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.manage_rel_btn.config(state=state)
        self.download_assets_btn.config(state=state)
        self.open_rel_web_btn.config(state=state)
        self.delete_rel_btn.config(state=state)

    def _new_release(self) -> None:
        CreateReleaseDialog(
            parent=self.dialog,
            repo=self.full_name,
            gh_manager=self.gh_manager,
            on_created=lambda tag: self._refresh_releases(),
        )

    def _manage_selected_release(self) -> None:
        rel = self._get_selected_release()
        if not rel:
            return
        tag = rel.get("tagName")
        if not tag:
            return

        ReleaseManagementDialog(
            parent=self.dialog,
            repo=self.full_name,
            tag=tag,
            gh_manager=self.gh_manager,
            on_updated=self._refresh_releases,
        )

    def _download_release_assets(self) -> None:
        rel = self._get_selected_release()
        if not rel:
            return
        tag = rel.get("tagName")
        if not tag:
            return

        dest_dir = filedialog.askdirectory(title=f"Select Download Folder for {tag} Assets", parent=self.dialog)
        if not dest_dir:
            return

        def _worker():
            try:
                # Use gh release download
                args = ["release", "download", tag, "--repo", self.full_name, "-D", str(dest_dir), "--clobber"]
                self.gh_manager.executor.run_text(args, timeout=300)
                self.dialog.after(0, lambda: messagebox.showinfo("Downloaded", f"Assets for {tag} downloaded to:\n{dest_dir}", parent=self.dialog))
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: messagebox.showerror("Download Error", f"Failed to download assets:\n{msg}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _open_selected_release_web(self) -> None:
        rel = self._get_selected_release()
        if not rel:
            return
        tag = rel.get("tagName")
        url = f"https://github.com/{self.full_name}/releases/tag/{tag}"
        self.gh_manager.open_in_browser(url)

    def _delete_selected_release(self) -> None:
        rel = self._get_selected_release()
        if not rel:
            return
        tag = rel.get("tagName")
        if not tag:
            return

        if not messagebox.askyesno(
            "Delete Release",
            f"Are you sure you want to delete release '{tag}' and all its assets?",
            parent=self.dialog,
        ):
            return

        typed = simpledialog.askstring(
            "Confirm Delete Release",
            f"To confirm deletion, please type the tag name exactly:\n{tag}",
            parent=self.dialog,
        )
        if typed != tag:
            if typed is not None:
                messagebox.showerror("Mismatch", "Tag name did not match. Deletion cancelled.", parent=self.dialog)
            return

        def _worker():
            try:
                self.gh_manager.releases.delete_release(self.full_name, tag)
                self.dialog.after(0, self._on_delete_success)
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Failed to delete release:\n{msg}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_delete_success(self) -> None:
        messagebox.showinfo("Release Deleted", "Release deleted successfully.", parent=self.dialog)
        self._refresh_releases()

    def _create_copy_row(self, parent: ttk.Frame, label: str, val: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=7).pack(side=tk.LEFT)
        entry = ttk.Entry(row, font=("Consolas", 8))
        entry.insert(0, val)
        entry.config(state="readonly")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        def copy_val():
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(val)
            btn.config(text="Copied!")
            self.dialog.after(1500, lambda: btn.config(text="Copy") if btn.winfo_exists() else None)

        btn = ttk.Button(row, text="Copy", width=8, command=copy_val)
        btn.pack(side=tk.RIGHT)

    def _open_web(self) -> None:
        url = self.repo.get("url") or f"https://github.com/{self.full_name}"
        self.gh_manager.open_in_browser(url)

    def _trigger_clone(self) -> None:
        self.dialog.destroy()
        if self.on_clone_requested and self.full_name:
            self.on_clone_requested(self.full_name)

    def _create_visibility_menu(self) -> None:
        self.vis_menu = tk.Menu(self.dialog, tearoff=0)

    def _show_visibility_menu(self, event=None) -> None:
        self.vis_menu.delete(0, tk.END)
        is_private = self.repo.get("isPrivate", False)
        if is_private:
            self.vis_menu.add_command(label="Make Public...", command=lambda: self._confirm_change_visibility(to_public=True))
        else:
            self.vis_menu.add_command(label="Make Private...", command=lambda: self._confirm_change_visibility(to_public=False))
        try:
            x = event.x_root if event else self.badge_lbl.winfo_rootx()
            y = event.y_root if event else self.badge_lbl.winfo_rooty() + self.badge_lbl.winfo_height()
            self.vis_menu.tk_popup(x, y)
        finally:
            self.vis_menu.grab_release()

    def _confirm_change_visibility(self, to_public: bool) -> None:
        target = "PUBLIC" if to_public else "PRIVATE"
        msg = (
            f"You are about to change '{self.full_name}' to {target}.\n\n"
            "CONSEQUENCES:\n"
            + ("• All code, commit history, and issues will become publicly accessible.\n"
               "• Anyone can clone and fork this repository.\n"
               "• Actions logs will become visible to the public."
               if to_public else
               "• Access will be restricted only to explicitly invited collaborators.\n"
               "• Public stars and watchers will be permanently removed.\n"
               "• Any public forks will be detached from the repository network.")
            + f"\n\nAre you sure you want to change visibility to {target}?"
        )
        if not messagebox.askyesno(f"Confirm Change to {target}", msg, icon=messagebox.WARNING, parent=self.dialog):
            return

        def _worker():
            try:
                self.gh_manager.repos.change_visibility(self.full_name, "public" if to_public else "private")
                self.dialog.after(0, lambda: self._on_visibility_changed(to_public, target))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: messagebox.showerror("Error", f"Failed to change visibility:\n{exc}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_visibility_changed(self, to_public: bool, target: str) -> None:
        self.repo["isPrivate"] = not to_public
        is_fork = self.repo.get("isFork", False)
        vis_text = f"{'Public' if to_public else 'Private'}{' (Fork)' if is_fork else ''} ▾"
        self.badge_lbl.config(text=vis_text, fg="#1a7f37" if to_public else "#cf222e")
        messagebox.showinfo("Visibility Changed", f"Repository '{self.full_name}' is now {target.lower()}!", parent=self.dialog)
