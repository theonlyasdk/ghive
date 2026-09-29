"""Asset upload dialog with live streaming metrics."""

import math
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

from core import GHManager


def format_size(bytes_val: float) -> str:
    """Format bytes into human readable string."""
    if bytes_val < 1024:
        return f"{int(bytes_val)} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"


def format_rate(rate_bytes_per_sec: float) -> str:
    """Format byte rate per second."""
    if rate_bytes_per_sec < 1024:
        return f"{rate_bytes_per_sec:.0f} B/s"
    elif rate_bytes_per_sec < 1024 * 1024:
        return f"{rate_bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{rate_bytes_per_sec / (1024 * 1024):.2f} MB/s"


def format_accel(accel_val: float) -> str:
    """Format rate acceleration (change in rate per second)."""
    sign = "+" if accel_val >= 0 else "-"
    abs_accel = abs(accel_val)
    if abs_accel < 1024:
        return f"{sign}{abs_accel:.0f} B/s²"
    elif abs_accel < 1024 * 1024:
        return f"{sign}{abs_accel / 1024:.1f} KB/s²"
    else:
        return f"{sign}{abs_accel / (1024 * 1024):.2f} MB/s²"


def format_eta(eta_seconds: float) -> str:
    """Format ETA seconds into human-readable string."""
    if eta_seconds <= 0 or math.isinf(eta_seconds) or math.isnan(eta_seconds):
        return "Calculating..."
    secs = int(eta_seconds)
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins:02d}:{rem_secs:02d}"


class AssetUploadProgressDialog:
    """Modal dialog displaying real-time metrics during release asset upload."""

    def __init__(
        self,
        parent: tk.Widget,
        repo: str,
        tag: str,
        file_path: str,
        gh_manager: GHManager,
        on_completed: Optional[Callable[[bool, Optional[str]], None]] = None,
    ):
        self.parent = parent
        self.repo = repo
        self.tag = tag
        self.file_path = Path(file_path)
        self.gh_manager = gh_manager
        self.on_completed = on_completed

        self.cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_closed = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Uploading Release Asset")
        self.dialog.geometry("480x280")
        self.dialog.minsize(440, 260)
        self.dialog.transient(parent)

        self._create_widgets()

        # Center relative to parent
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 480
            dh = 280
            cx = px + (pw // 2) - (dw // 2)
            cy = py + (ph // 2) - (dh // 2)
            self.dialog.geometry(f"{dw}x{dh}+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        try:
            self.dialog.grab_set()
        except Exception:
            pass

        # Start upload worker
        self._start_upload()

    def _create_widgets(self) -> None:
        container = ttk.Frame(self.dialog, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        filename = self.file_path.name
        try:
            self.total_size = self.file_path.stat().st_size
        except Exception:
            self.total_size = 0

        self.file_lbl = ttk.Label(
            container,
            text=f"Uploading: {filename}",
            font=("Segoe UI", 10, "bold"),
            foreground="#0969da",
        )
        self.file_lbl.pack(anchor=tk.W, pady=(0, 4))

        self.size_lbl = ttk.Label(
            container,
            text=f"Target: {self.repo} @ {self.tag} | Total: {format_size(self.total_size)}",
            foreground="#57606a",
        )
        self.size_lbl.pack(anchor=tk.W, pady=(0, 12))

        # Progress bar
        self.progress_bar = ttk.Progressbar(container, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # Percentage & Transferred
        stats_top = ttk.Frame(container)
        stats_top.pack(fill=tk.X, pady=(0, 8))

        self.percent_lbl = ttk.Label(stats_top, text="0.0%", font=("Segoe UI", 9, "bold"))
        self.percent_lbl.pack(side=tk.LEFT)

        self.transferred_lbl = ttk.Label(stats_top, text=f"0 B / {format_size(self.total_size)}", foreground="#57606a")
        self.transferred_lbl.pack(side=tk.RIGHT)

        # Real-time metrics box (Live rate, Acceleration, ETA)
        metrics_box = ttk.LabelFrame(container, text="Live Upload Metrics", padding=8)
        metrics_box.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(metrics_box, text="Current Rate:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        self.rate_val = ttk.Label(metrics_box, text="0 KB/s", font=("Consolas", 9, "bold"))
        self.rate_val.grid(row=0, column=1, sticky=tk.W, padx=4, pady=2)

        ttk.Label(metrics_box, text="Rate Change:").grid(row=0, column=2, sticky=tk.W, padx=(16, 4), pady=2)
        self.accel_val = ttk.Label(metrics_box, text="0 KB/s²", font=("Consolas", 9))
        self.accel_val.grid(row=0, column=3, sticky=tk.W, padx=4, pady=2)

        ttk.Label(metrics_box, text="ETA:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        self.eta_val = ttk.Label(metrics_box, text="Calculating...", font=("Consolas", 9))
        self.eta_val.grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)

        # Bottom Button Bar
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.cancel_btn = ttk.Button(btn_bar, text="Cancel Upload", command=self._on_cancel, width=14)
        self.cancel_btn.pack(side=tk.RIGHT)

    def _start_upload(self) -> None:
        def _worker():
            try:
                self.gh_manager.releases.upload_asset_streaming(
                    repo=self.repo,
                    tag=self.tag,
                    file_path=self.file_path,
                    progress_callback=self._update_progress_safe,
                    cancel_event=self.cancel_event,
                )
                if not self._is_closed:
                    self.dialog.after(0, self._on_success)
            except Exception as exc:
                if not self._is_closed:
                    err = exc
                    self.dialog.after(0, lambda e=err: self._on_error(e))

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def _update_progress_safe(self, uploaded: int, total: int, rate: float, accel: float, eta: float) -> None:
        if self._is_closed:
            return
        try:
            self.dialog.after(0, lambda u=uploaded, t=total, r=rate, a=accel, e=eta: self._apply_metrics(u, t, r, a, e))
        except Exception:
            pass

    def _apply_metrics(self, uploaded: int, total: int, rate: float, accel: float, eta: float) -> None:
        if self._is_closed:
            return
        pct = (uploaded / total * 100.0) if total > 0 else 0.0
        self.progress_bar["value"] = pct
        self.percent_lbl.config(text=f"{pct:.1f}%")
        self.transferred_lbl.config(text=f"{format_size(uploaded)} / {format_size(total)}")
        self.rate_val.config(text=format_rate(rate))
        self.accel_val.config(text=format_accel(accel))
        self.eta_val.config(text=format_eta(eta))

    def _on_success(self) -> None:
        self._is_closed = True
        self.progress_bar["value"] = 100
        self.percent_lbl.config(text="100.0%")
        self.dialog.destroy()
        if self.on_completed:
            self.on_completed(True, None)

    def _on_error(self, exc: Exception) -> None:
        self._is_closed = True
        is_cancel = isinstance(exc, InterruptedError) or self.cancel_event.is_set()
        err_msg = "Upload cancelled." if is_cancel else str(exc)
        self.dialog.destroy()
        if not is_cancel:
            messagebox.showerror("Upload Error", f"Failed to upload asset:\n{err_msg}", parent=self.parent)
        if self.on_completed:
            self.on_completed(False, err_msg)

    def _on_cancel(self) -> None:
        if messagebox.askyesno("Cancel Upload", "Are you sure you want to cancel this upload?", parent=self.dialog):
            self.cancel_event.set()
            self.cancel_btn.config(state=tk.DISABLED, text="Cancelling...")
