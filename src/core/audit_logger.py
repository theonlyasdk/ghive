"""Audit logger for recording user operations and actions in ghive."""

import datetime
from pathlib import Path
from typing import Optional


class AuditLogger:
    """Logs user actions and command executions to ~/.ghive/audit.log."""

    _log_file = Path.home() / ".ghive" / "audit.log"

    @classmethod
    def get_log_path(cls) -> Path:
        """Return the path to the audit log file."""
        return cls._log_file

    @classmethod
    def log(cls, target: Optional[str], operation: str, details: str = "") -> None:
        """Write an audit entry to ~/.ghive/audit.log.

        Args:
            target: Context target (e.g., 'owner/repo', 'gist:id', or 'GLOBAL').
            operation: Name of the operation performed.
            details: Additional details or arguments.
        """
        try:
            cls._log_file.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            context = target if target else "GLOBAL"
            entry = f"[{timestamp}] [{context}] {operation}"
            if details:
                entry += f" - {details}"
            entry += "\n"

            with open(cls._log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass
