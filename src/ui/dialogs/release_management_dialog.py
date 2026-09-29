"""Comprehensive release and asset management dialog."""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional

from core import GHManager
from ui.dialogs.asset_upload_dialog import AssetUploadProgressDialog, format_size
from ui.widgets import ErrorView, LoadingOverlay


class ReleaseManagementDialog:
    """Dialog for comprehensive management of a GitHub release and its artifacts."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        tag: str,
        gh_manager: GHManager,
        on_updated: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.tag = tag
        self.gh_manager = gh_manager
        self.on_updated = on_updated

        self.release_data: Dict[str, Any] = {}
        self.assets: List[Dict[str, Any]] = []

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Release Management - {repo} @ {tag}")
        self.dialog.geometry("740x632")
        self.dialog.minsize(640, 532)
        self.dialog.transient(parent)

        self._create_widgets()
        self._load_release_data()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 740
            dh = 632
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
        self.error_view = ErrorView(self.dialog, on_retry=self._load_release_data, on_close=self.dialog.destroy)

        self.main_container = ttk.Frame(self.dialog, padding=14)
        container = self.main_container
        container.pack(fill=tk.BOTH, expand=True)

        # Header area
        header_frame = ttk.Frame(container)
        header_frame.pack(fill=tk.X, pady=(0, 8))

        self.tag_label = ttk.Label(header_frame, text=f"Release {self.tag}", font=("Segoe UI", 13, "bold"), foreground="#0969da")
        self.tag_label.pack(side=tk.LEFT)

        self.badge_frame = ttk.Frame(header_frame)
        self.badge_frame.pack(side=tk.RIGHT)

        self.meta_label = ttk.Label(container, text="Loading release details...", foreground="#57606a")
        self.meta_label.pack(anchor=tk.W, pady=(0, 10))

        # Title and Description Frame
        details_box = ttk.LabelFrame(container, text="Release Information", padding=10)
        details_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        title_row = ttk.Frame(details_box)
        title_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(title_row, text="Title:").pack(side=tk.LEFT, padx=(0, 8))
        self.title_entry = ttk.Entry(title_row)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.save_btn = ttk.Button(title_row, text="Save Changes", command=self._save_changes)
        self.save_btn.pack(side=tk.RIGHT)

        ttk.Label(details_box, text="Release Notes / Description:").pack(anchor=tk.W, pady=(0, 4))
        self.body_text = scrolledtext.ScrolledText(details_box, height=5, font=("Segoe UI", 9), wrap=tk.WORD)
        self.body_text.pack(fill=tk.BOTH, expand=True)

        # Artifacts / Assets Section
        assets_box = ttk.LabelFrame(container, text="Release Assets / Artifacts", padding=10)
        assets_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tree_frame = ttk.Frame(assets_box)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("Name", "Size", "Downloads", "Created")
        self.assets_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse", height=5)
        for col in cols:
            self.assets_tree.heading(col, text=col)

        self.assets_tree.column("Name", width=300)
        self.assets_tree.column("Size", width=90, anchor="center")
        self.assets_tree.column("Downloads", width=90, anchor="center")
        self.assets_tree.column("Created", width=130, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.assets_tree.yview)
        self.assets_tree.configure(yscrollcommand=scroll.set)

        self.assets_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.assets_tree.bind("<<TreeviewSelect>>", lambda e: self._update_asset_btn_states())

        # Asset buttons
        asset_btns = ttk.Frame(assets_box)
        asset_btns.pack(fill=tk.X)

        self.upload_btn = ttk.Button(asset_btns, text="Upload Asset...", command=self._upload_asset)
        self.upload_btn.pack(side=tk.LEFT, padx=2)

        self.download_btn = ttk.Button(asset_btns, text="Download Asset...", command=self._download_asset, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=2)

        self.delete_asset_btn = ttk.Button(asset_btns, text="Delete Asset", command=self._delete_asset, state=tk.DISABLED)
        self.delete_asset_btn.pack(side=tk.LEFT, padx=2)

        self.copy_url_btn = ttk.Button(asset_btns, text="Copy Download URL", command=self._copy_asset_url, state=tk.DISABLED)
        self.copy_url_btn.pack(side=tk.LEFT, padx=2)

        # Dialog bottom bar
        bottom_bar = ttk.Frame(container)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.delete_rel_btn = ttk.Button(bottom_bar, text="Delete Release...", command=self._delete_release)
        self.delete_rel_btn.pack(side=tk.LEFT)

        ttk.Button(bottom_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(bottom_bar, text="Open in Browser", command=self._open_in_browser, width=14).pack(side=tk.RIGHT, padx=6)

    def _load_release_data(self) -> None:
        self.loading_overlay.show()
        self.error_view.hide()
        self.main_container.pack_forget()

        def _task():
            return self.gh_manager.releases.view_release(self.repo, self.tag)

        def _on_success(data):
            self.loading_overlay.hide()
            self.error_view.hide()
            self.main_container.pack(fill=tk.BOTH, expand=True)
            self.release_data = data
            self._populate_release_fields()

        def _on_error(exc):
            self.loading_overlay.hide()
            self.main_container.pack_forget()
            self.error_view.show(f"Failed to load release data:\n{exc}")

        def _worker():
            try:
                res = _task()
                self.dialog.after(0, lambda r=res: _on_success(r))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: _on_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_release_fields(self) -> None:
        data = self.release_data
        title = data.get("name") or self.tag
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, title)

        body = data.get("body") or ""
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert(tk.END, body)

        for w in self.badge_frame.winfo_children():
            w.destroy()

        if data.get("isLatest"):
            ttk.Label(self.badge_frame, text="[Latest]", foreground="#1a7f37", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        if data.get("isPrerelease"):
            ttk.Label(self.badge_frame, text="[Pre-release]", foreground="#9a6700", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        if data.get("isDraft"):
            ttk.Label(self.badge_frame, text="[Draft]", foreground="#cf222e", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)

        pub_date = (data.get("publishedAt") or data.get("createdAt") or "").replace("T", " ").replace("Z", "")[:16]
        author = data.get("author", {}).get("login", "") if isinstance(data.get("author"), dict) else ""
        meta_str = f"Published: {pub_date}"
        if author:
            meta_str += f" by @{author}"
        self.meta_label.config(text=meta_str)

        self.assets = data.get("assets", []) or []
        self._populate_assets_tree()

    def _populate_assets_tree(self) -> None:
        for item in self.assets_tree.get_children():
            self.assets_tree.delete(item)

        for a in self.assets:
            name = a.get("name", "Unknown")
            size = format_size(a.get("size", 0))
            downloads = str(a.get("downloadCount", 0))
            created = (a.get("createdAt") or "").replace("T", " ").replace("Z", "")[:16]
            self.assets_tree.insert("", tk.END, values=(name, size, downloads, created))

        self._update_asset_btn_states()

    def _get_selected_asset(self) -> Optional[Dict[str, Any]]:
        sel = self.assets_tree.selection()
        if not sel:
            return None
        idx = self.assets_tree.index(sel[0])
        if 0 <= idx < len(self.assets):
            return self.assets[idx]
        return None

    def _update_asset_btn_states(self) -> None:
        has_sel = self._get_selected_asset() is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self.download_btn.config(state=state)
        self.delete_asset_btn.config(state=state)
        self.copy_url_btn.config(state=state)

    def _save_changes(self) -> None:
        new_title = self.title_entry.get().strip()
        new_notes = self.body_text.get("1.0", tk.END).strip()

        self.save_btn.config(state=tk.DISABLED, text="Saving...")

        def _worker():
            try:
                self.gh_manager.releases.edit_release(self.repo, self.tag, title=new_title, notes=new_notes)
                self.dialog.after(0, self._on_save_success)
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: self._on_save_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_save_success(self) -> None:
        self.save_btn.config(state=tk.NORMAL, text="Save Changes")
        messagebox.showinfo("Saved", "Release details updated successfully.", parent=self.dialog)
        if self.on_updated:
            self.on_updated()

    def _on_save_error(self, exc: Exception) -> None:
        self.save_btn.config(state=tk.NORMAL, text="Save Changes")
        messagebox.showerror("Error", f"Failed to save changes:\n{exc}", parent=self.dialog)

    def _upload_asset(self) -> None:
        filepath = filedialog.askopenfilename(title="Select Asset File to Upload", parent=self.dialog)
        if not filepath:
            return

        p = Path(filepath)
        if not p.is_file():
            messagebox.showerror("File Error", "Selected file does not exist.", parent=self.dialog)
            return

        size = p.stat().st_size
        if size > 2 * 1024 * 1024 * 1024:
            messagebox.showerror(
                "File Too Large",
                f"The file size ({format_size(size)}) exceeds GitHub's 2GB release asset limit.\nGitHub will reject this upload.",
                parent=self.dialog,
            )
            return

        # Check for duplicate asset name
        existing_names = [a.get("name") for a in self.assets]
        if p.name in existing_names:
            if not messagebox.askyesno(
                "Duplicate Asset",
                f"An asset named '{p.name}' already exists in this release.\nDo you want to overwrite it?",
                parent=self.dialog,
            ):
                return

        def _on_upload_done(success: bool, err_msg: Optional[str]):
            if success:
                messagebox.showinfo("Upload Complete", f"Successfully uploaded '{p.name}'!", parent=self.dialog)
                self._load_release_data()
                if self.on_updated:
                    self.on_updated()

        AssetUploadProgressDialog(
            parent=self.dialog,
            repo=self.repo,
            tag=self.tag,
            file_path=str(p),
            gh_manager=self.gh_manager,
            on_completed=_on_upload_done,
        )

    def _download_asset(self) -> None:
        asset = self._get_selected_asset()
        if not asset:
            return
        name = asset.get("name")
        if not name:
            return

        dest_dir = filedialog.askdirectory(title=f"Select Download Folder for {name}", parent=self.dialog)
        if not dest_dir:
            return

        def _worker():
            try:
                self.gh_manager.releases.download_asset(self.repo, self.tag, name, dest_dir)
                self.dialog.after(0, lambda: messagebox.showinfo("Downloaded", f"Asset '{name}' downloaded successfully to:\n{dest_dir}", parent=self.dialog))
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: messagebox.showerror("Download Error", f"Failed to download asset:\n{msg}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _delete_asset(self) -> None:
        asset = self._get_selected_asset()
        if not asset:
            return
        name = asset.get("name", "")

        if not messagebox.askyesno("Delete Asset", f"Are you sure you want to delete asset '{name}'?\nThis cannot be undone.", parent=self.dialog):
            return

        def _worker():
            try:
                self.gh_manager.releases.delete_asset(self.repo, self.tag, name)
                self.dialog.after(0, self._on_delete_asset_success)
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Failed to delete asset:\n{msg}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_delete_asset_success(self) -> None:
        messagebox.showinfo("Asset Deleted", "Asset deleted successfully.", parent=self.dialog)
        self._load_release_data()
        if self.on_updated:
            self.on_updated()

    def _copy_asset_url(self) -> None:
        asset = self._get_selected_asset()
        if not asset:
            return
        url = asset.get("url") or asset.get("apiUrl") or f"https://github.com/{self.repo}/releases/download/{self.tag}/{asset.get('name')}"
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(url)
        self.copy_url_btn.config(text="Copied!")
        self.dialog.after(1500, lambda: self.copy_url_btn.config(text="Copy Download URL") if self.copy_url_btn.winfo_exists() else None)

    def _delete_release(self) -> None:
        if not messagebox.askyesno(
            "Delete Release",
            f"Are you sure you want to delete release '{self.tag}' and all its assets?",
            parent=self.dialog,
        ):
            return

        typed = simpledialog.askstring(
            "Confirm Delete Release",
            f"To confirm deletion, please type the tag name exactly:\n{self.tag}",
            parent=self.dialog,
        )
        if typed != self.tag:
            if typed is not None:
                messagebox.showerror("Mismatch", "Tag name did not match. Deletion cancelled.", parent=self.dialog)
            return

        def _worker():
            try:
                self.gh_manager.releases.delete_release(self.repo, self.tag)
                self.dialog.after(0, self._on_delete_release_success)
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Failed to delete release:\n{msg}", parent=self.dialog))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_delete_release_success(self) -> None:
        messagebox.showinfo("Release Deleted", f"Release '{self.tag}' deleted successfully.", parent=self.parent)
        self.dialog.destroy()
        if self.on_updated:
            self.on_updated()

    def _open_in_browser(self) -> None:
        url = self.release_data.get("url") or f"https://github.com/{self.repo}/releases/tag/{self.tag}"
        self.gh_manager.open_in_browser(url)
