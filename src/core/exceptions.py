"""Custom exceptions for GitHub CLI operations."""

from typing import Optional, List


class GHCLIError(RuntimeError):
    """Base exception for all GitHub CLI operations."""
    pass


class GHNotFoundError(GHCLIError):
    """Raised when the gh executable is not found on PATH or configured location."""
    pass


class GHAuthError(GHCLIError):
    """Raised when authentication fails or user is not logged in."""
    pass


class GHNetworkError(GHCLIError):
    """Raised when a network timeout or connectivity error occurs."""
    pass


class GHCommandError(GHCLIError):
    """Raised when a gh command exits with a non-zero exit status."""

    def __init__(
        self,
        message: str,
        command: Optional[List[str]] = None,
        returncode: int = 1,
        stdout: str = "",
        stderr: str = ""
    ):
        super().__init__(message)
        self.command = command or []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
