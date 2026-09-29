"""Dependency manager for checking and locating gh and git binaries."""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config_manager import ConfigManager
from .exceptions import GHNotFoundError


class DependencyManager:
    """Detects, validates, and manages external CLI tools (gh, git)."""

    def __init__(self):
        self.system = platform.system().lower()
        self.config = ConfigManager()

    def get_gh_path(self) -> Path:
        """Locate the GitHub CLI (gh) executable."""
        # Check custom path in config
        custom_path = self.config.get("paths", "gh", "")
        if custom_path and Path(custom_path).is_file():
            return Path(custom_path)

        # Check system PATH
        gh_which = shutil.which("gh")
        if gh_which:
            return Path(gh_which)

        # Check common platform directories
        common_paths = self._get_common_gh_paths()
        for p in common_paths:
            if p.is_file():
                return p

        raise GHNotFoundError(
            "GitHub CLI ('gh') executable was not found. "
            "Please install GitHub CLI or specify its path in Preferences."
        )

    def get_git_path(self) -> Optional[Path]:
        """Locate Git executable (optional helper for cloning)."""
        custom_path = self.config.get("paths", "git", "")
        if custom_path and Path(custom_path).is_file():
            return Path(custom_path)

        git_which = shutil.which("git")
        if git_which:
            return Path(git_which)

        common_paths = self._get_common_git_paths()
        for p in common_paths:
            if p.is_file():
                return p
        return None

    def get_gh_version(self, gh_path: Optional[Path] = None) -> str:
        """Return the version string of the installed gh binary."""
        path = gh_path or self.get_gh_path()
        try:
            startupinfo = None
            if self.system == "windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=startupinfo,
            )
            first_line = res.stdout.strip().split("\n")[0]
            return first_line if first_line else "Unknown"
        except Exception:
            return "Unknown"

    def _get_common_gh_paths(self) -> List[Path]:
        paths = []
        home = Path.home()
        if self.system == "windows":
            paths.extend(
                [
                    Path("C:/Program Files/GitHub CLI/gh.exe"),
                    Path("C:/Program Files (x86)/GitHub CLI/gh.exe"),
                    home / "AppData/Local/Programs/GitHub CLI/gh.exe",
                    home / "scoop/shims/gh.exe",
                    Path("C:/ProgramData/chocolatey/bin/gh.exe"),
                ]
            )
        elif self.system == "darwin":
            paths.extend(
                [
                    Path("/opt/homebrew/bin/gh"),
                    Path("/usr/local/bin/gh"),
                    home / ".local/bin/gh",
                ]
            )
        else:  # Linux / Unix
            paths.extend(
                [
                    Path("/usr/bin/gh"),
                    Path("/usr/local/bin/gh"),
                    Path("/snap/bin/gh"),
                    home / ".local/bin/gh",
                ]
            )
        return paths

    def _get_common_git_paths(self) -> List[Path]:
        paths = []
        home = Path.home()
        if self.system == "windows":
            paths.extend(
                [
                    Path("C:/Program Files/Git/cmd/git.exe"),
                    Path("C:/Program Files/Git/bin/git.exe"),
                    Path("C:/Program Files (x86)/Git/cmd/git.exe"),
                    home / "AppData/Local/Programs/Git/cmd/git.exe",
                    home / "scoop/shims/git.exe",
                ]
            )
        elif self.system == "darwin":
            paths.extend(
                [
                    Path("/opt/homebrew/bin/git"),
                    Path("/usr/local/bin/git"),
                    Path("/usr/bin/git"),
                ]
            )
        else:
            paths.extend(
                [
                    Path("/usr/bin/git"),
                    Path("/usr/local/bin/git"),
                ]
            )
        return paths

    @staticmethod
    def get_install_guide() -> Dict[str, Tuple[str, str]]:
        """Return download URL and package manager command for platforms."""
        return {
            "windows": (
                "https://github.com/cli/cli/releases/latest",
                "winget install --id GitHub.cli",
            ),
            "darwin": (
                "https://github.com/cli/cli/releases/latest",
                "brew install gh",
            ),
            "linux": (
                "https://github.com/cli/cli/blob/trunk/docs/install_linux.md",
                "sudo apt install gh",
            ),
        }
