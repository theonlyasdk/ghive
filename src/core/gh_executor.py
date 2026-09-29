"""Low-level GitHub CLI subprocess execution engine."""

import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from .exceptions import (
    GHAuthError,
    GHCLIError,
    GHCommandError,
    GHNetworkError,
    GHNotFoundError,
)

_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class GHExecutor:
    """Executes gh subprocess commands with proper error handling and JSON parsing."""

    def __init__(self, gh_path: Union[str, Path]):
        self.gh_path = str(gh_path)
        self.system = platform.system().lower()

    @staticmethod
    def sanitize_output(text: str) -> str:
        """Strip ANSI escape sequences and trailing whitespace."""
        if not text:
            return ""
        cleaned = _ANSI_ESCAPE_RE.sub("", text)
        return cleaned.strip()

    def run_raw(
        self,
        args: List[str],
        cwd: Optional[Union[str, Path]] = None,
        stdin_input: Optional[str] = None,
        timeout: int = 60,
    ) -> Tuple[str, str, int]:
        """Execute a raw gh command and return (stdout, stderr, returncode)."""
        cmd = [self.gh_path] + args

        startupinfo = None
        creationflags = 0
        if self.system == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            res = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                input=stdin_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            return res.stdout, res.stderr, res.returncode
        except FileNotFoundError:
            raise GHNotFoundError(
                f"GitHub CLI binary was not found at '{self.gh_path}'. "
                "Please configure the path in Preferences."
            )
        except subprocess.TimeoutExpired:
            raise GHNetworkError(f"Command timed out after {timeout} seconds: {' '.join(args)}")

    def run_text(
        self,
        args: List[str],
        cwd: Optional[Union[str, Path]] = None,
        stdin_input: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        """Execute command and return stdout as cleaned text, raising on error."""
        stdout, stderr, returncode = self.run_raw(args, cwd, stdin_input, timeout)
        clean_stdout = self.sanitize_output(stdout)
        clean_stderr = self.sanitize_output(stderr)

        if returncode != 0:
            lower_err = clean_stderr.lower()
            if (
                "not logged into" in lower_err
                or "to authenticate, run: gh auth login" in lower_err
                or "authentication failed" in lower_err
                or "bad credentials" in lower_err
                or "http 401" in lower_err
            ):
                raise GHAuthError(clean_stderr or "GitHub authentication failed or user is not logged in.")
            elif (
                "could not resolve host" in lower_err
                or "connection refused" in lower_err
                or "timed out" in lower_err
            ):
                raise GHNetworkError(clean_stderr or "Network error while connecting to GitHub.")
            else:
                raise GHCommandError(
                    clean_stderr or f"Command failed with exit code {returncode}",
                    command=args,
                    returncode=returncode,
                    stdout=clean_stdout,
                    stderr=clean_stderr,
                )

        return clean_stdout

    def run_json(
        self,
        args: List[str],
        cwd: Optional[Union[str, Path]] = None,
        stdin_input: Optional[str] = None,
        timeout: int = 60,
    ) -> Any:
        """Execute command and parse stdout as JSON."""
        output = self.run_text(args, cwd=cwd, stdin_input=stdin_input, timeout=timeout)
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise GHCLIError(f"Failed to parse JSON response: {exc}\nRaw Output: {output[:300]}")
