"""Main window for ghive application."""

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional, Union

from core import AsyncRunner, ConfigManager, GHManager
from ui.dialogs import AboutDialog, AuthDialog, CloneRepoDialog, CreateRepoDialog, PreferencesDialog
from ui.tabs import GistsTab, IssuesTab, PRsTab, ReposTab, RunsTab
from ui.theme import setup_theme
from ui.widgets import StatusBar


class MainWindow:
    """Main application window for ghive."""

    def __init__(
        self,
        gh_path: Optional[Union[str, Path]] = None,
    ):
        self.root = tk.Tk()
        self.root.title("ghive - GitHub CLI Frontend")
        self.root.geometry("960x660")
        self.root.minsize(640, 480)

        # Setup styling
        setup_theme(self.root)

        # Core managers
        self.config = ConfigManager()
        self.gh_manager = GHManager(gh_path)
        self.async_runner = AsyncRunner(self.root)

        self.active_repo: str = self.config.get("general", "active_repo", "")

        # Build UI
        self._create_ui()

        # Center on screen
        self._center_window(960, 660)

        # Bindings & protocols
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._setup_shortcuts()

        # Periodic signal check for responsive Ctrl+C handling
        self._check_signals()

        # Initial background loads
        self.root.after(100, self._initial_load)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            cx = (sw // 2) - (width // 2)
            cy = (sh // 2) - (height // 2)
            self.root.geometry(f"{width}x{height}+{max(0, cx)}+{max(0, cy)}")
        except Exception:
            pass

    def _create_ui(self) -> None:
        self._create_menu()
        self._create_notebook()
        self._create_statusbar()

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Preferences...", command=self._show_preferences, accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Authentication Status...", command=self._show_auth_dialog)
        file_menu.add_command(label="Refresh All", command=self._refresh_all, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing, accelerator="Ctrl+Q")

        # Repository Menu
        repo_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Repository", menu=repo_menu)
        repo_menu.add_command(label="New Repository...", command=self._new_repo, accelerator="Ctrl+N")
        repo_menu.add_command(label="Clone Repository...", command=self._clone_repo, accelerator="Ctrl+Shift+O")
        repo_menu.add_separator()
        repo_menu.add_command(label="Open Active Repo in Browser", command=self._open_active_repo_in_browser)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="GitHub CLI Manual", command=self._open_gh_manual)
        help_menu.add_separator()
        help_menu.add_command(label="About ghive", command=self._show_about)

    def _create_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        # Repos Tab
        self.repos_tab = ReposTab(
            self.notebook,
            self.gh_manager,
            self.async_runner,
            self.set_status,
            on_active_repo_changed=self._on_active_repo_changed,
        )

        # Issues Tab
        self.issues_tab = IssuesTab(
            self.notebook,
            self.gh_manager,
            self.async_runner,
            self.set_status,
        )

        # Pull Requests Tab
        self.prs_tab = PRsTab(
            self.notebook,
            self.gh_manager,
            self.async_runner,
            self.set_status,
        )

        # Workflow Runs Tab
        self.runs_tab = RunsTab(
            self.notebook,
            self.gh_manager,
            self.async_runner,
            self.set_status,
        )

        # Gists Tab
        self.gists_tab = GistsTab(
            self.notebook,
            self.gh_manager,
            self.async_runner,
            self.set_status,
        )

        self.notebook.add(self.repos_tab, text="Repositories")
        self.notebook.add(self.issues_tab, text="Issues")
        self.notebook.add(self.prs_tab, text="Pull Requests")
        self.notebook.add(self.runs_tab, text="Actions")
        self.notebook.add(self.gists_tab, text="Gists")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _create_statusbar(self) -> None:
        self.statusbar = StatusBar(self.root, on_auth_click=self._show_auth_dialog)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_shortcuts(self) -> None:
        self.root.bind("<Control-comma>", lambda e: self._show_preferences())
        self.root.bind("<Control-q>", lambda e: self._on_closing())
        self.root.bind("<F5>", lambda e: self._refresh_current_tab())
        self.root.bind("<Control-n>", lambda e: self._new_repo())
        self.root.bind("<Control-Shift-O>", lambda e: self._clone_repo())

    def _initial_load(self) -> None:
        self._check_auth()
        self.repos_tab.refresh()

    def _check_auth(self) -> None:
        def _task():
            return self.gh_manager.auth.get_status()

        def _on_success(status):
            user = status.get("user", "")
            host = status.get("host", "github.com")
            logged_in = status.get("logged_in", False)
            self.statusbar.set_user_info(user, host, logged_in)

        self.async_runner.run(_task, on_success=_on_success)

    def _on_active_repo_changed(self, repo_name: str) -> None:
        self.active_repo = repo_name
        self.config.set("general", "active_repo", repo_name)
        self.issues_tab.set_active_repo(repo_name)
        self.prs_tab.set_active_repo(repo_name)
        self.runs_tab.set_active_repo(repo_name)
        self.set_status(f"Active repository set to {repo_name}")

    def _on_tab_changed(self, event=None) -> None:
        current_tab_id = self.notebook.select()
        if not current_tab_id:
            return

        tab_text = self.notebook.tab(current_tab_id, "text")
        if tab_text == "Repositories" and not self.repos_tab.repos:
            self.repos_tab.refresh()
        elif tab_text == "Issues" and self.active_repo and not self.issues_tab.issues:
            self.issues_tab.set_active_repo(self.active_repo)
        elif tab_text == "Pull Requests" and self.active_repo and not self.prs_tab.prs:
            self.prs_tab.set_active_repo(self.active_repo)
        elif tab_text == "Actions" and self.active_repo and not self.runs_tab.runs:
            self.runs_tab.set_active_repo(self.active_repo)
        elif tab_text == "Gists" and not self.gists_tab.gists:
            self.gists_tab.refresh()

    def _refresh_current_tab(self) -> None:
        current_tab_id = self.notebook.select()
        if not current_tab_id:
            return
        tab_text = self.notebook.tab(current_tab_id, "text")
        if tab_text == "Repositories":
            self.repos_tab.refresh()
        elif tab_text == "Issues":
            self.issues_tab.refresh()
        elif tab_text == "Pull Requests":
            self.prs_tab.refresh()
        elif tab_text == "Actions":
            self.runs_tab.refresh()
        elif tab_text == "Gists":
            self.gists_tab.refresh()

    def _refresh_all(self) -> None:
        self._check_auth()
        self.repos_tab.refresh()
        if self.active_repo:
            self.issues_tab.refresh()
            self.prs_tab.refresh()
            self.runs_tab.refresh()
        self.gists_tab.refresh()
        self.set_status("Refreshing all tabs...")

    def set_status(self, text: str, is_error: bool = False, is_warning: bool = False) -> None:
        """Update main status bar message."""
        self.statusbar.set_status(text, is_error=is_error, is_warning=is_warning)

    def _show_preferences(self) -> None:
        PreferencesDialog(self.root, on_preferences_changed=self._on_preferences_changed).show()

    def _on_preferences_changed(self) -> None:
        self.set_status("Preferences updated")
        self._check_auth()

    def _show_auth_dialog(self) -> None:
        AuthDialog(self.root, self.gh_manager, on_auth_change=self._refresh_all)

    def _new_repo(self) -> None:
        CreateRepoDialog(self.root, self.gh_manager, on_created=lambda name: self.repos_tab.refresh())

    def _clone_repo(self) -> None:
        CloneRepoDialog(
            self.root,
            self.gh_manager,
            default_repo=self.active_repo,
            on_cloned=lambda repo, path: self.set_status(f"Cloned {repo} to {path}"),
        )

    def _open_active_repo_in_browser(self) -> None:
        if self.active_repo:
            self.gh_manager.open_in_browser(self.active_repo)
        else:
            messagebox.showinfo("No Active Repository", "Please select a repository first.", parent=self.root)

    def _open_gh_manual(self) -> None:
        self.gh_manager.open_in_browser("https://cli.github.com/manual/")

    def _show_about(self) -> None:
        AboutDialog(self.root).show()

    def _on_closing(self) -> None:
        self.root.destroy()

    def _check_signals(self) -> None:
        """Periodic heartbeat allowing Python interpreter to handle OS signals like SIGINT."""
        try:
            self.root.after(200, self._check_signals)
        except Exception:
            pass

    def run(self) -> None:
        """Start the main event loop."""
        self.root.mainloop()
