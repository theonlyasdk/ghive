"""Unified GitHub manager aggregating all core operations."""

import webbrowser
from pathlib import Path
from typing import Optional, Union

from .config_manager import ConfigManager
from .dependency_manager import DependencyManager
from .gh_auth import GHAuth
from .gh_executor import GHExecutor
from .gh_gists import GHGists
from .gh_issues import GHIssues
from .gh_prs import GHPRs
from .gh_releases import GHReleases
from .gh_repos import GHRepos
from .gh_runs import GHRuns


class GHManager:
    """Central façade orchestrating GitHub CLI operations."""

    def __init__(self, gh_path: Optional[Union[str, Path]] = None):
        self.config = ConfigManager()
        self.dep_manager = DependencyManager()

        if gh_path is None:
            self.gh_path = self.dep_manager.get_gh_path()
        else:
            self.gh_path = Path(gh_path)

        self.executor = GHExecutor(self.gh_path)
        self.auth = GHAuth(self.executor)
        self.repos = GHRepos(self.executor)
        self.releases = GHReleases(self.executor)
        self.issues = GHIssues(self.executor)
        self.prs = GHPRs(self.executor)
        self.runs = GHRuns(self.executor)
        self.gists = GHGists(self.executor)

    def open_in_browser(self, url_or_target: str) -> bool:
        """Open a GitHub URL or target in the default web browser."""
        if not url_or_target:
            return False

        if url_or_target.startswith("http://") or url_or_target.startswith("https://"):
            return webbrowser.open(url_or_target)
        else:
            # If passed e.g. "cli/cli" or "owner/repo"
            target_url = f"https://github.com/{url_or_target}"
            return webbrowser.open(target_url)
