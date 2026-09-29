"""Gist details and file preview dialog with multi-page management."""

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, Optional

from core import GHManager
from ui.widgets import ErrorView, LoadingOverlay


class GistDetailsDialog:
    """Dialog displaying gist files, previewing contents, managing pages and sharing."""

    def __init__(
        self,
        parent: tk.Widget,
        gist_data: Dict[str, Any],
        gh_manager: GHManager,
        on_clone_requested: Optional[Callable[[str], None]] = None,
        on_updated: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.gist_summary = gist_data
        self.gist_id = gist_data.get("id", "")
        self.gh_manager = gh_manager
        self.on_clone_requested = on_clone_requested
        self.on_updated = on_updated

        self.files_dict: Dict[str, Any] = {}
        self.current_filename: Optional[str] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Gist Details - {self.gist_id[:8]}")
        self.dialog.geometry("900x668")
        self.dialog.minsize(780, 568)
        self.dialog.transient(parent)

        self._create_menu()
        self._create_visibility_menu()
        self._create_widgets()
        self._load_gist_content()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 900
            dh = 668
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

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.dialog)
        self.dialog.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Page to Gist...", command=self._add_page, accelerator="Ctrl+N")
        file_menu.add_command(label="Rename Current Page...", command=self._rename_page)
        file_menu.add_command(label="Delete Current Page", command=self._delete_page)
        file_menu.add_separator()
        file_menu.add_command(label="Clone Gist Locally...", command=self._trigger_clone)
        file_menu.add_command(label="Delete Gist...", command=self._delete_gist)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.dialog.destroy, accelerator="Esc")

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Edit Gist Description...", command=self._rename_gist)
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy Gist ID", command=self._copy_id)
        edit_menu.add_command(label="Copy Page Content", command=self._copy_content)
        edit_menu.add_command(label="Copy Gist URL", command=self._copy_url)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Open in Browser", command=self._open_web)
        view_menu.add_command(label="Reload Gist", command=self._load_gist_content, accelerator="F5")

        self.dialog.bind("<Control-n>", lambda e: self._add_page())
        self.dialog.bind("<F5>", lambda e: self._load_gist_content())

    def _create_widgets(self) -> None:
        self.loading_overlay = LoadingOverlay(self.dialog, text="Loading...")
        self.error_view = ErrorView(self.dialog, on_retry=self._load_gist_content, on_close=self.dialog.destroy)

        self.main_container = ttk.Frame(self.dialog, padding=(14, 10, 14, 4))
        container = self.main_container
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 6))

        # Lighter font for Gist name, 8pt larger
        light_title_font = getattr(self.dialog, "app_font_light_header", ("Segoe UI Light", 19))
        desc = self.gist_summary.get("description") or "(No description)"

        self.title_lbl = tk.Label(
            header,
            text=desc,
            font=light_title_font,
            fg="#0969da",
            anchor=tk.W,
            cursor="hand2",
        )
        self.title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.title_lbl.bind("<Double-1>", lambda e: self._rename_gist())

        is_public = self.gist_summary.get("public", False)
        self.badge_lbl = tk.Label(
            header,
            text=f"{'Public' if is_public else 'Secret'} ▾",
            font=("Segoe UI", 9, "bold"),
            fg="#1a7f37" if is_public else "#57606a",
            cursor="hand2",
        )
        self.badge_lbl.pack(side=tk.RIGHT)
        self.badge_lbl.bind("<Button-1>", self._show_visibility_menu)

        # Page / File selector row
        files_frame = ttk.Frame(container)
        files_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(files_frame, text="Page:").pack(side=tk.LEFT, padx=(0, 4))
        self.file_var = tk.StringVar()
        self.file_cb = ttk.Combobox(files_frame, textvariable=self.file_var, state="readonly", width=26)
        self.file_cb.pack(side=tk.LEFT, padx=(0, 6))
        self.file_cb.bind("<<ComboboxSelected>>", self._on_file_selected)

        ttk.Button(files_frame, text="+ Add Page", command=self._add_page, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(files_frame, text="Rename", command=self._rename_page, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(files_frame, text="Delete", command=self._delete_page, width=7).pack(side=tk.LEFT, padx=2)

        self.copy_content_btn = ttk.Button(files_frame, text="Copy Content", command=self._copy_content)
        self.copy_content_btn.pack(side=tk.RIGHT)
        ttk.Button(files_frame, text="Save Changes", command=self._save_content).pack(side=tk.RIGHT, padx=4)

        # Content text area
        text_frame = ttk.Frame(container)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.content_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 9), relief=tk.SOLID, bd=1)
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.content_text.xview)
        self.content_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Button row above status bar
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Open in Browser", command=self._open_web, width=14).pack(side=tk.RIGHT, padx=6)

        if self.on_clone_requested:
            ttk.Button(btn_bar, text="Clone Gist...", command=self._trigger_clone, width=12).pack(side=tk.LEFT)

        # Bottom status bar: show Gist ID in black/default text color + small copy button
        self.statusbar = ttk.Frame(self.dialog, relief=tk.SUNKEN, padding=(6, 3))
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.id_label = ttk.Label(
            self.statusbar,
            text=f"Gist ID: {self.gist_id}",
            font=("Segoe UI", 9),
            foreground="black",
        )
        self.id_label.pack(side=tk.LEFT, padx=(2, 4))

        self.copy_id_btn = ttk.Button(
            self.statusbar,
            text="Copy",
            command=self._copy_id,
            width=7,
        )
        self.copy_id_btn.pack(side=tk.LEFT)

        self.status_info = ttk.Label(
            self.statusbar,
            text="",
            font=("Segoe UI", 9),
            foreground="#57606a",
            anchor=tk.E,
        )
        self.status_info.pack(side=tk.RIGHT, padx=4)

    def _load_gist_content(self) -> None:
        self.loading_overlay.show()
        self.error_view.hide()
        self.main_container.pack_forget()
        self.status_info.config(text="Loading...")

        def _worker():
            try:
                full_data = self.gh_manager.gists.view_gist(self.gist_id)
                self.dialog.after(0, lambda d=full_data: self._on_gist_loaded(d))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: self._on_gist_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_gist_loaded(self, full_data: Dict[str, Any]) -> None:
        self.loading_overlay.hide()
        self.error_view.hide()
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.files_dict = full_data.get("files", {})

        new_desc = full_data.get("description") or "(No description)"
        self.title_lbl.config(text=new_desc)

        file_names = list(self.files_dict.keys())
        if file_names:
            self.file_cb["values"] = file_names
            target = self.current_filename if self.current_filename in file_names else file_names[0]
            self.file_cb.set(target)
            self._display_file(target)
            self.status_info.config(text=f"{len(file_names)} file(s)")
        else:
            self.file_cb["values"] = []
            self.file_cb.set("")
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert("1.0", "(No files in gist)")
            self.status_info.config(text="0 files")

    def _on_gist_error(self, err_msg: str) -> None:
        self.loading_overlay.hide()
        self.main_container.pack_forget()
        self.error_view.show(f"Failed to load gist content:\n{err_msg}")
        self.status_info.config(text="Error")

    def _on_file_selected(self, event=None) -> None:
        chosen = self.file_var.get()
        if chosen:
            self._display_file(chosen)

    def _display_file(self, filename: str) -> None:
        self.current_filename = filename
        file_obj = self.files_dict.get(filename, {})
        content = file_obj.get("content", "(Binary or truncated content)")
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", content)

    def _save_content(self) -> None:
        if not self.current_filename:
            return
        content = self.content_text.get("1.0", tk.END)
        try:
            self.status_info.config(text=f"Saving {self.current_filename}...")
            self.gh_manager.gists.update_file_content(self.gist_id, self.current_filename, content)
            messagebox.showinfo("Saved", f"Changes to '{self.current_filename}' saved successfully!", parent=self.dialog)
            self._load_gist_content()
        except Exception as e:
            messagebox.showerror("Save Failed", f"Failed to save content:\n{e}", parent=self.dialog)

    def _add_page(self) -> None:
        filename = simpledialog.askstring("Add Page to Gist", "Enter filename for the new page (e.g. notes.md):", parent=self.dialog)
        if not filename or not filename.strip():
            return
        clean_name = filename.strip()
        try:
            self.status_info.config(text=f"Adding {clean_name}...")
            self.gh_manager.gists.add_file(self.gist_id, clean_name, " ")
            self.current_filename = clean_name
            self._load_gist_content()
            messagebox.showinfo("Success", f"Page '{clean_name}' added to gist!", parent=self.dialog)
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error Adding Page", str(e), parent=self.dialog)

    def _rename_page(self) -> None:
        if not self.current_filename:
            return
        new_name = simpledialog.askstring(
            "Rename Page",
            f"Enter new filename for '{self.current_filename}':",
            initialvalue=self.current_filename,
            parent=self.dialog,
        )
        if not new_name or not new_name.strip() or new_name.strip() == self.current_filename:
            return
        clean_name = new_name.strip()
        try:
            self.status_info.config(text=f"Renaming to {clean_name}...")
            self.gh_manager.gists.rename_file(self.gist_id, self.current_filename, clean_name)
            self.current_filename = clean_name
            self._load_gist_content()
            messagebox.showinfo("Success", f"Page renamed to '{clean_name}'!", parent=self.dialog)
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error Renaming Page", str(e), parent=self.dialog)

    def _delete_page(self) -> None:
        if not self.current_filename:
            return
        if len(self.files_dict) <= 1:
            messagebox.showwarning("Cannot Delete", "A gist must have at least one file. Cannot delete the only page.", parent=self.dialog)
            return

        if not messagebox.askyesno("Confirm Delete", f"Delete page '{self.current_filename}' from this gist?", parent=self.dialog):
            return

        try:
            self.status_info.config(text=f"Deleting {self.current_filename}...")
            self.gh_manager.gists.delete_file(self.gist_id, self.current_filename)
            self.current_filename = None
            self._load_gist_content()
            messagebox.showinfo("Success", "Page deleted successfully!", parent=self.dialog)
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error Deleting Page", str(e), parent=self.dialog)

    def _rename_gist(self) -> None:
        current_desc = self.gist_summary.get("description", "")
        new_desc = simpledialog.askstring(
            "Edit Gist Description",
            "Enter new description for this gist:",
            initialvalue=current_desc,
            parent=self.dialog,
        )
        if new_desc is None:
            return

        clean_desc = new_desc.strip()
        try:
            self.status_info.config(text="Updating description...")
            self.gh_manager.gists.update_description(self.gist_id, clean_desc)
            self.gist_summary["description"] = clean_desc
            self.title_lbl.config(text=clean_desc or "(No description)")
            self.status_info.config(text="Description updated")
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update description:\n{e}", parent=self.dialog)

    def _create_visibility_menu(self) -> None:
        self.visibility_menu = tk.Menu(self.dialog, tearoff=0)
        self.visibility_menu.add_command(label="Make Public", command=self._confirm_make_public)
        self.visibility_menu.add_command(label="Make Secret", command=self._confirm_make_secret)

    def _show_visibility_menu(self, event=None) -> None:
        is_public = self.gist_summary.get("public", False)
        self.visibility_menu.entryconfigure("Make Public", state=tk.DISABLED if is_public else tk.NORMAL)
        self.visibility_menu.entryconfigure("Make Secret", state=tk.NORMAL if is_public else tk.DISABLED)
        x = self.badge_lbl.winfo_rootx()
        y = self.badge_lbl.winfo_rooty() + self.badge_lbl.winfo_height() + 2
        self.visibility_menu.post(x, y)

    def _confirm_make_public(self) -> None:
        if self.gist_summary.get("public", False):
            return

        msg = (
            "Convert Gist to Public?\n\n"
            "Consequences of making this Gist Public:\n"
            "• Public gists are visible to everyone on the internet.\n"
            "• It will appear in GitHub's public Discover feed and your profile.\n"
            "• Search engines can index the gist and its code.\n"
            "• Anyone can clone, fork, and star this gist.\n\n"
            "Note: GitHub visibility is immutable per Gist ID. ghive will create a new "
            "Public Gist with all current pages and delete the original secret gist.\n"
            "The gist will receive a new Gist ID and URL.\n\n"
            "Do you want to proceed with making this gist Public?"
        )
        if not messagebox.askyesno("Confirm: Make Gist Public", msg, icon=messagebox.WARNING, parent=self.dialog):
            return

        self._convert_gist_visibility(to_public=True)

    def _confirm_make_secret(self) -> None:
        if not self.gist_summary.get("public", False):
            return

        msg = (
            "Convert Gist to Secret?\n\n"
            "Consequences of making this Gist Secret:\n"
            "• Secret gists do not appear in GitHub Discover or search engine indexes.\n"
            "• It will not be listed on your public GitHub profile.\n"
            "• Anyone with the direct URL can still view it.\n\n"
            "Note: GitHub visibility is immutable per Gist ID. ghive will create a new "
            "Secret Gist with all current pages and delete the original public gist.\n"
            "Existing external links to the old Gist ID will become invalid.\n\n"
            "Do you want to proceed with making this gist Secret?"
        )
        if not messagebox.askyesno("Confirm: Make Gist Secret", msg, icon=messagebox.WARNING, parent=self.dialog):
            return

        self._convert_gist_visibility(to_public=False)

    def _convert_gist_visibility(self, to_public: bool) -> None:
        target_name = "Public" if to_public else "Secret"
        self.status_info.config(text=f"Converting to {target_name}...")

        def _worker():
            try:
                new_id = self.gh_manager.gists.change_visibility(self.gist_id, to_public=to_public)
                if not new_id:
                    raise RuntimeError("Failed to create new gist with desired visibility.")
                self.dialog.after(0, lambda nid=new_id, tp=to_public: self._on_visibility_changed(nid, tp))
            except Exception as e:
                err_msg = str(e)
                self.dialog.after(0, lambda msg=err_msg: self._on_visibility_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_visibility_changed(self, new_id: str, to_public: bool) -> None:
        target_name = "Public" if to_public else "Secret"
        self.gist_id = new_id
        self.gist_summary["id"] = new_id
        self.gist_summary["public"] = to_public
        self.dialog.title(f"Gist Details - {self.gist_id[:8]}")
        self.id_label.config(text=f"Gist ID: {self.gist_id}")
        self.badge_lbl.config(
            text=f"{'Public' if to_public else 'Secret'} ▾",
            fg="#1a7f37" if to_public else "#57606a",
        )
        self._load_gist_content()
        self.status_info.config(text=f"Converted to {target_name}")
        messagebox.showinfo(
            "Visibility Changed",
            f"Gist successfully converted to {target_name}!\nNew Gist ID: {new_id}",
            parent=self.dialog,
        )
        if self.on_updated:
            self.on_updated()

    def _on_visibility_error(self, exc: Exception) -> None:
        self.status_info.config(text="Error changing visibility")
        messagebox.showerror("Error", f"Failed to change gist visibility:\n{exc}", parent=self.dialog)

    def _delete_gist(self) -> None:
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete gist '{self.gist_id}'?", parent=self.dialog):
            return
        verify = simpledialog.askstring("Confirm Delete", "Type 'DELETE' to confirm deletion:", parent=self.dialog)
        if verify != "DELETE":
            messagebox.showinfo("Cancelled", "Deletion aborted.", parent=self.dialog)
            return

        try:
            self.gh_manager.gists.delete_gist(self.gist_id)
            messagebox.showinfo("Deleted", "Gist permanently deleted.", parent=self.dialog)
            self.dialog.destroy()
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Delete Failed", str(e), parent=self.dialog)

    def _copy_id(self) -> None:
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(self.gist_id)
        self.copy_id_btn.config(text="Copied!")
        self.dialog.after(1500, lambda: self.copy_id_btn.config(text="Copy") if self.copy_id_btn.winfo_exists() else None)

    def _copy_content(self) -> None:
        content = self.content_text.get("1.0", tk.END).strip()
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(content)
        self.copy_content_btn.config(text="Copied!")
        self.dialog.after(1500, lambda: self.copy_content_btn.config(text="Copy Content") if self.copy_content_btn.winfo_exists() else None)

    def _copy_url(self) -> None:
        url = self.gist_summary.get("url") or f"https://gist.github.com/{self.gist_id}"
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(url)
        self.status_info.config(text="Gist URL copied to clipboard!")

    def _trigger_clone(self) -> None:
        self.dialog.destroy()
        if self.on_clone_requested:
            self.on_clone_requested(self.gist_id)

    def _open_web(self) -> None:
        url = self.gist_summary.get("url") or f"https://gist.github.com/{self.gist_id}"
        self.gh_manager.open_in_browser(url)
