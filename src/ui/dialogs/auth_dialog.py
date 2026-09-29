"""Authentication management dialog."""

import io
import platform
import queue
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from tkinter import messagebox, ttk
from typing import Callable, Optional

from core import GHManager

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None


class AuthDialog:
    """Dialog for inspecting authentication status and logging in via token."""

    def __init__(self, parent: tk.Widget, gh_manager: GHManager, on_auth_change: Optional[Callable[[], None]] = None):
        self.parent = parent
        self.gh_manager = gh_manager
        self.on_auth_change = on_auth_change

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Your GitHub Account")
        self.dialog.geometry("520x560")
        self.dialog.minsize(480, 520)
        self.dialog.transient(parent)
        self.profile: dict = {}
        self._avatar_image = None
        self._avatar_loading = False
        self._shimmer_offset = -40
        self._refresh_generation = 0
        self._status_results = queue.Queue()

        self._create_widgets()
        self.dialog.after(100, self._poll_status_results)
        self._refresh_status()

        # Center dialog
        self.dialog.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 520
            dh = 560
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
        container = ttk.Frame(self.dialog, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        status_box = ttk.LabelFrame(container, text="Your GitHub Account", padding=12)
        status_box.pack(fill=tk.X, pady=(0, 12))

        profile_row = ttk.Frame(status_box)
        profile_row.pack(fill=tk.X)
        self.avatar_holder = tk.Frame(profile_row, width=96, height=96, background="#e5e7eb")
        self.avatar_holder.pack(side=tk.LEFT, padx=(0, 12))
        self.avatar_holder.pack_propagate(False)
        self.avatar_canvas = tk.Canvas(self.avatar_holder, width=96, height=96, highlightthickness=0, background="#e5e7eb")
        self.avatar_lbl = tk.Label(self.avatar_holder, text="", font=("Segoe UI", 9), fg="#57606a", bg="#f6f8fa")
        identity = ttk.Frame(profile_row)
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.user_lbl = tk.Label(identity, text="", font=("Segoe UI", 12, "bold"), anchor=tk.W)
        self.user_lbl.pack(fill=tk.X, pady=(2, 0))
        self.name_lbl = tk.Label(identity, text="", font=("Segoe UI", 9), fg="#57606a", anchor=tk.W, wraplength=330, justify=tk.LEFT)
        self.name_lbl.pack(fill=tk.X, pady=2)

        self.host_lbl = tk.Label(status_box, text="Host: github.com", font=("Segoe UI", 9), fg="#57606a", anchor=tk.W)
        self.host_lbl.pack(fill=tk.X, pady=1)

        self.scopes_lbl = tk.Label(status_box, text="Scopes: -", font=("Segoe UI", 8), fg="#57606a", anchor=tk.W)
        self.scopes_lbl.pack(fill=tk.X, pady=1)

        self.profile_stats_lbl = tk.Label(status_box, text="", font=("Segoe UI", 8), fg="#57606a", anchor=tk.W)
        self.profile_stats_lbl.pack(fill=tk.X, pady=1)

        login_box = ttk.LabelFrame(container, text="Log In with Personal Access Token", padding=12)
        login_box.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        token_help = tk.Label(
            login_box,
            text="Generate a Personal Access Token (classic or fine-grained) with 'repo', 'read:org', and 'workflow' scopes.",
            font=("Segoe UI", 8),
            fg="#57606a",
            wraplength=420,
            justify=tk.LEFT,
        )
        token_help.pack(anchor=tk.W, pady=(0, 6))

        token_row = ttk.Frame(login_box)
        token_row.pack(fill=tk.X, pady=4)

        ttk.Label(token_row, text="Token:").pack(side=tk.LEFT, padx=(0, 6))
        self.token_entry = ttk.Entry(token_row, show="*", width=34)
        self.token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.show_token_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(token_row, text="Show", variable=self.show_token_var, command=self._toggle_token_visibility).pack(side=tk.LEFT)

        btn_row = ttk.Frame(login_box)
        btn_row.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(btn_row, text="Get Token Online", command=self._open_token_page).pack(side=tk.LEFT)
        self.login_btn = ttk.Button(btn_row, text="Authenticate", command=self._on_login_click)
        self.login_btn.pack(side=tk.RIGHT)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Close", command=self.dialog.destroy, width=10).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Refresh", command=self._refresh_status, width=10).pack(side=tk.RIGHT, padx=6)
        self.logout_btn = ttk.Button(btn_bar, text="Log Out", command=self._on_logout_click, width=10)
        self.logout_btn.pack(side=tk.LEFT)
        self.profile_btn = ttk.Button(btn_bar, text="View Profile", command=self._open_profile, width=12, state=tk.DISABLED)
        self.profile_btn.pack(side=tk.LEFT, padx=(6, 0))

        light_font = "Segoe UI Light" if platform.system().lower() == "windows" else "Helvetica Neue Light"
        self.loading_overlay = tk.Frame(self.dialog, background="#ffffff")
        self.loading_label = tk.Label(
            self.loading_overlay,
            text="Loading...",
            font=(light_font, 24),
            foreground="#57606a",
            background="#ffffff",
        )
        self.loading_label.place(relx=0.5, rely=0.46, anchor=tk.CENTER)
        self.loading_bar = ttk.Progressbar(self.loading_overlay, mode="indeterminate", length=190)
        self.loading_bar.place(relx=0.5, rely=0.56, anchor=tk.CENTER)

    def _toggle_token_visibility(self) -> None:
        self.token_entry.config(show="" if self.show_token_var.get() else "*")

    def _open_token_page(self) -> None:
        webbrowser.open("https://github.com/settings/tokens/new?scopes=repo,read:org,workflow,gist&description=ghive-cli")

    def _refresh_status(self) -> None:
        self._refresh_generation += 1
        generation = self._refresh_generation
        self._stop_avatar_shimmer()
        self._set_loading(True)

        def worker():
            try:
                status = self.gh_manager.auth.get_status()
                profile = self.gh_manager.auth.get_profile() if status.get("logged_in") else {}
                result = (status, profile, None)
            except Exception as exc:
                result = (None, {}, str(exc))
            self._status_results.put((generation, *result))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_status_results(self) -> None:
        if not self.dialog.winfo_exists():
            return
        while True:
            try:
                result = self._status_results.get_nowait()
            except queue.Empty:
                break
            if result[0] == "login":
                self._on_login_finished(result[1])
            elif result[0] == "logout":
                self._on_logout_finished(result[1])
            elif result[0] == "avatar":
                self._show_avatar(result[1], result[2])
            else:
                self._show_status(*result)
        try:
            self.dialog.after(100, self._poll_status_results)
        except tk.TclError:
            pass

    @staticmethod
    def _download_avatar(url: str) -> Optional[bytes]:
        if not url.startswith("https://"):
            return None
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ghive/1.0",
                    "Accept": "image/png,image/jpeg,image/gif,*/*;q=0.5",
                    "Referer": "https://github.com/",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(3 * 1024 * 1024 + 1)
            return data if len(data) <= 3 * 1024 * 1024 else None
        except (OSError, ValueError, urllib.error.URLError):
            return None

    def _set_loading(self, loading: bool, text: str = "Loading...") -> None:
        if loading:
            self.loading_label.config(text=text)
            self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.loading_overlay.lift()
            self.loading_bar.start(12)
        else:
            self.loading_bar.stop()
            self.loading_overlay.place_forget()

    def _show_status(self, generation: int, status, profile: dict, error: Optional[str]) -> None:
        if generation != self._refresh_generation or not self.dialog.winfo_exists():
            return
        self._set_loading(False)
        self.profile = profile or {}
        if error:
            self.user_lbl.config(text="Unable to load account", fg="#cf222e")
            self.name_lbl.config(text=error)
            self.host_lbl.config(text="Host: github.com")
            self.scopes_lbl.config(text="Scopes: —")
            self.profile_stats_lbl.config(text="")
            self.logout_btn.config(state=tk.DISABLED)
            self.profile_btn.config(state=tk.DISABLED)
            return

        if not status or not status.get("logged_in"):
            self.user_lbl.config(text="Not logged in", fg="#cf222e")
            self.name_lbl.config(text="Authenticate with a personal access token below")
            self.host_lbl.config(text="Host: github.com")
            self.scopes_lbl.config(text="Scopes: None")
            self.profile_stats_lbl.config(text="")
            self._show_avatar_unavailable()
            self.logout_btn.config(state=tk.DISABLED)
            self.profile_btn.config(state=tk.DISABLED)
            return

        user = profile.get("login") or status.get("user", "Unknown")
        display_name = profile.get("name") or "GitHub account"
        bio = profile.get("bio") or ""
        self.user_lbl.config(text=f"@{user}", fg="#1a7f37")
        self.name_lbl.config(text=f"{display_name} · {bio}" if bio else display_name)
        self.host_lbl.config(text=f"Host: {status.get('host', 'github.com')}")
        self.scopes_lbl.config(text=f"Scopes: {', '.join(status.get('scopes', [])) or 'Standard'}")
        stats = []
        if "public_repos" in profile:
            stats.append(f"{profile['public_repos']} public repositories")
        if "followers" in profile:
            stats.append(f"{profile['followers']} followers")
        self.profile_stats_lbl.config(text=" · ".join(stats))
        self._load_avatar(generation, profile, user)
        self.logout_btn.config(state=tk.NORMAL)
        self.profile_btn.config(state=tk.NORMAL if profile.get("html_url") else tk.DISABLED)

    def _load_avatar(self, generation: int, profile: dict, username: str) -> None:
        self.avatar_lbl.place_forget()
        self._avatar_loading = True
        self._shimmer_offset = -40
        self.avatar_canvas.pack(fill=tk.BOTH, expand=True)
        self._draw_avatar_shimmer()

        urls = []
        profile_id = profile.get("id")
        if profile_id:
            urls.append(f"https://avatars.githubusercontent.com/u/{profile_id}?v=4")
        avatar_url = profile.get("avatar_url", "")
        if avatar_url:
            urls.append(avatar_url)
        if username:
            urls.append(f"https://github.com/{username}.png?size=128")

        def worker():
            avatar_data = None
            for url in dict.fromkeys(urls):
                avatar_data = self._download_avatar(url)
                if avatar_data:
                    break
            self._status_results.put(("avatar", generation, avatar_data))

        threading.Thread(target=worker, daemon=True).start()

    def _draw_avatar_shimmer(self) -> None:
        if not self._avatar_loading or not self.dialog.winfo_exists():
            return
        self.avatar_canvas.delete("all")
        for y in range(0, 96, 8):
            band_center = self._shimmer_offset + 0.35 * y
            for x in range(0, 96, 8):
                distance = abs(x + 4 - band_center)
                color = "#f4f5f7" if distance < 10 else ("#eceef1" if distance < 22 else "#e5e7eb")
                self.avatar_canvas.create_rectangle(x, y, x + 8, y + 8, fill=color, outline=color)
        self._shimmer_offset += 8
        if self._shimmer_offset > 140:
            self._shimmer_offset = -40
        self.dialog.after(55, self._draw_avatar_shimmer)

    def _stop_avatar_shimmer(self) -> None:
        self._avatar_loading = False

    def _show_avatar_unavailable(self) -> None:
        self._stop_avatar_shimmer()
        self.avatar_canvas.pack_forget()
        self.avatar_lbl.config(image="", text="Unavailable", width=14, height=4)
        self.avatar_lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self._avatar_image = None

    def _show_avatar(self, generation: int, image_data: Optional[bytes]) -> None:
        if generation != self._refresh_generation or not self.dialog.winfo_exists():
            return
        self._stop_avatar_shimmer()
        if not image_data:
            self._show_avatar_unavailable()
            return
        try:
            if Image is not None:
                avatar = Image.open(io.BytesIO(image_data)).convert("RGB")
                avatar.thumbnail((96, 96))
                photo = ImageTk.PhotoImage(avatar, master=self.dialog)
            else:
                photo = tk.PhotoImage(data=image_data, master=self.dialog)
            self._avatar_image = photo
        except (tk.TclError, OSError, ValueError):
            self._show_avatar_unavailable()
            return
        self.avatar_canvas.pack_forget()
        self.avatar_lbl.config(image=photo, text="", width=96, height=96)
        self.avatar_lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _open_profile(self) -> None:
        url = self.profile.get("html_url")
        if url:
            webbrowser.open(url)

    def _on_login_click(self) -> None:
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showwarning("Missing Token", "Please paste your Personal Access Token.", parent=self.dialog)
            return

        self.login_btn.config(state=tk.DISABLED, text="Authenticating...")
        self._set_loading(True)

        def worker():
            try:
                self.gh_manager.auth.login_with_token(token)
                result = None
            except Exception as exc:
                result = str(exc)
            self._status_results.put(("login", result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_login_finished(self, error: Optional[str]) -> None:
        if not self.dialog.winfo_exists():
            return
        self.login_btn.config(state=tk.NORMAL, text="Authenticate")
        self._set_loading(False)
        if error:
            messagebox.showerror("Authentication Failed", error, parent=self.dialog)
            return
        self.token_entry.delete(0, tk.END)
        messagebox.showinfo("Success", "Successfully authenticated with GitHub!", parent=self.dialog)
        self._refresh_status()
        if self.on_auth_change:
            self.on_auth_change()

    def _on_logout_click(self) -> None:
        if messagebox.askyesno("Confirm Log Out", "Are you sure you want to log out of GitHub CLI?", parent=self.dialog):
            self.logout_btn.config(state=tk.DISABLED)
            self._set_loading(True)

            def worker():
                try:
                    self.gh_manager.auth.logout()
                    result = None
                except Exception as exc:
                    result = str(exc)
                self._status_results.put(("logout", result))

            threading.Thread(target=worker, daemon=True).start()

    def _on_logout_finished(self, error: Optional[str]) -> None:
        if not self.dialog.winfo_exists():
            return
        self._set_loading(False)
        if error:
            self.logout_btn.config(state=tk.NORMAL)
            messagebox.showerror("Error", error, parent=self.dialog)
            return
        self._refresh_status()
        if self.on_auth_change:
            self.on_auth_change()
