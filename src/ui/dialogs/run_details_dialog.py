import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core import GHManager
from ui.widgets import ErrorView, LoadingOverlay


class RunDetailsDialog:
    """Dialog displaying GitHub Actions workflow run logs and actions."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        run_data: Dict[str, Any],
        gh_manager: GHManager,
        on_updated: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.run_data = run_data
        self.run_id = run_data.get("databaseId")
        self.gh_manager = gh_manager
        self.on_updated = on_updated
        self.full_log = ""

        self.dialog = tk.Toplevel(parent)
        name = run_data.get("workflowName") or run_data.get("name", "Workflow Run")
        self.dialog.title(f"Workflow Run #{self.run_id} - {name}")
        self.dialog.geometry("720x620")
        self.dialog.minsize(620, 500)
        self.dialog.transient(parent)

        self._create_widgets()
        self._load_log()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 720
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
        self.loading_overlay = LoadingOverlay(self.dialog, text="Loading Logs...")
        self.error_view = ErrorView(self.dialog, on_retry=self._load_log, on_close=self.dialog.destroy)

        self.main_container = ttk.Frame(self.dialog, padding=14)
        container = self.main_container
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 4))

        wf_name = self.run_data.get("workflowName") or self.run_data.get("name", "Workflow")
        title_lbl = tk.Label(header, text=f"{wf_name} (#{self.run_id})", font=("Segoe UI", 12, "bold"), fg="#0969da", anchor=tk.W)
        title_lbl.pack(side=tk.LEFT)

        status = self.run_data.get("status", "unknown").upper()
        conclusion = (self.run_data.get("conclusion") or "").upper()
        badge_text = f"[{conclusion or status}]"

        color = "#57606a"
        if conclusion == "SUCCESS":
            color = "#1a7f37"
        elif conclusion in ("FAILURE", "TIMED_OUT"):
            color = "#cf222e"
        elif status == "IN_PROGRESS":
            color = "#9a6700"

        badge_lbl = tk.Label(header, text=badge_text, font=("Segoe UI", 9, "bold"), fg=color)
        badge_lbl.pack(side=tk.RIGHT)

        branch = self.run_data.get("headBranch", "branch")
        event = self.run_data.get("event", "event")
        created = self.run_data.get("createdAt", "").replace("T", " ").replace("Z", "")

        meta_lbl = tk.Label(
            container,
            text=f"Branch: {branch} | Trigger: {event} | Created: {created}",
            font=("Segoe UI", 8),
            fg="#57606a",
            anchor=tk.W,
        )
        meta_lbl.pack(fill=tk.X, pady=(0, 8))

        log_box = ttk.LabelFrame(container, text="Execution Logs", padding=8)
        log_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        search_row = ttk.Frame(log_box)
        search_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(search_row, text="Filter log:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_entry = ttk.Entry(search_row, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", self._filter_log)

        self.copy_log_btn = ttk.Button(search_row, text="Copy Full Log", command=self._copy_log)
        self.copy_log_btn.pack(side=tk.RIGHT)

        text_frame = ttk.Frame(log_box)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 9), relief=tk.SOLID, bd=1)
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Open in Browser", command=self._open_web, width=14).pack(side=tk.RIGHT, padx=6)

        self.rerun_btn = ttk.Button(btn_bar, text="Rerun Workflow", command=self._rerun, width=15)
        self.rerun_btn.pack(side=tk.LEFT, padx=(0, 6))

        if status == "IN_PROGRESS":
            self.cancel_btn = ttk.Button(btn_bar, text="Cancel Run", command=self._cancel, width=12)
            self.cancel_btn.pack(side=tk.LEFT)

    def _load_log(self) -> None:
        self.loading_overlay.show()
        self.error_view.hide()
        self.main_container.pack_forget()

        def _worker():
            try:
                log_data = self.gh_manager.runs.get_run_log(self.repo, self.run_id)
                self.dialog.after(0, lambda l=log_data: self._on_log_loaded(l))
            except Exception as e:
                err = e
                self.dialog.after(0, lambda exc=err: self._on_log_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_log_loaded(self, log_data: str) -> None:
        self.loading_overlay.hide()
        self.error_view.hide()
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.full_log = log_data if log_data else "(No logs recorded)"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert("1.0", self.full_log)
        self.log_text.config(state=tk.DISABLED)

    def _on_log_error(self, err_msg: str) -> None:
        self.loading_overlay.hide()
        self.main_container.pack_forget()
        self.error_view.show(f"Failed to retrieve workflow log:\n{err_msg}")

    def _filter_log(self, event=None) -> None:
        query = self.search_entry.get().strip().lower()
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)

        if not query:
            self.log_text.insert("1.0", self.full_log)
        else:
            filtered_lines = [l for l in self.full_log.splitlines() if query in l.lower()]
            if filtered_lines:
                self.log_text.insert("1.0", "\n".join(filtered_lines))
            else:
                self.log_text.insert("1.0", f"(No lines matching '{query}')")

        self.log_text.config(state=tk.DISABLED)

    def _copy_log(self) -> None:
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(self.full_log)
        self.copy_log_btn.config(text="Copied!")
        self.dialog.after(1500, lambda: self.copy_log_btn.config(text="Copy Full Log") if self.copy_log_btn.winfo_exists() else None)

    def _rerun(self) -> None:
        self.rerun_btn.config(state=tk.DISABLED)
        try:
            self.gh_manager.runs.rerun(self.repo, self.run_id)
            messagebox.showinfo("Workflow Triggered", f"Run #{self.run_id} has been restarted.", parent=self.dialog)
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rerun workflow:\n{e}", parent=self.dialog)
        finally:
            self.rerun_btn.config(state=tk.NORMAL)

    def _cancel(self) -> None:
        try:
            self.gh_manager.runs.cancel(self.repo, self.run_id)
            messagebox.showinfo("Cancelled", f"Run #{self.run_id} cancelled.", parent=self.dialog)
            if self.on_updated:
                self.on_updated()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to cancel workflow:\n{e}", parent=self.dialog)

    def _open_web(self) -> None:
        url = self.run_data.get("url") or f"https://github.com/{self.repo}/actions/runs/{self.run_id}"
        self.gh_manager.open_in_browser(url)
