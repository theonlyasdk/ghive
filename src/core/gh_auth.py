"""GitHub authentication management via gh auth."""

import re
from typing import Any, Dict, Optional

from .audit_logger import AuditLogger
from .exceptions import GHAuthError
from .gh_executor import GHExecutor


class GHAuth:
    """Manages GitHub authentication status, logins, and accounts."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def get_status(self) -> Dict[str, Any]:
        """Check current authentication status across hosts."""
        stdout, stderr, returncode = self.executor.run_raw(["auth", "status"])
        output = (stdout + "\n" + stderr).strip()

        info: Dict[str, Any] = {
            "logged_in": False,
            "user": "Unknown",
            "host": "github.com",
            "active": False,
            "scopes": [],
            "raw": output,
        }

        # Check for success pattern
        if "Logged in to" in output:
            info["logged_in"] = True
            user_match = re.search(r"Logged in to [^\s]+ account ([^\s\(\)]+)", output)
            if user_match:
                info["user"] = user_match.group(1)

            host_match = re.search(r"Logged in to ([^\s]+) account", output)
            if host_match:
                info["host"] = host_match.group(1)

            if "Active account: true" in output:
                info["active"] = True

            scopes_match = re.search(r"Token scopes: '([^']+)'", output)
            if scopes_match:
                info["scopes"] = [s.strip() for s in scopes_match.group(1).split(",")]

        # Secondary check via API if logged in but username unknown
        if info["logged_in"] and info["user"] == "Unknown":
            try:
                user_login = self.executor.run_text(["api", "user", "--jq", ".login"])
                if user_login:
                    info["user"] = user_login.strip()
            except Exception:
                pass

        return info

    def get_username(self) -> str:
        """Get the current authenticated user login name."""
        status = self.get_status()
        if status.get("logged_in") and status.get("user") != "Unknown":
            return status["user"]
        try:
            user = self.executor.run_text(["api", "user", "--jq", ".login"])
            return user.strip()
        except Exception:
            return ""

    def get_profile(self) -> Dict[str, Any]:
        """Return the authenticated user's public GitHub profile."""
        profile = self.executor.run_json(["api", "user"])
        return profile if isinstance(profile, dict) else {}

    def login_with_token(self, token: str, host: str = "github.com") -> bool:
        """Authenticate using a Personal Access Token (PAT)."""
        if not token or not token.strip():
            raise GHAuthError("Token cannot be empty.")

        clean_token = token.strip()
        args = ["auth", "login", "--hostname", host, "--with-token"]
        stdout, stderr, returncode = self.executor.run_raw(args, stdin_input=clean_token)

        if returncode != 0:
            err = self.executor.sanitize_output(stderr or stdout)
            raise GHAuthError(f"Login failed: {err}")

        AuditLogger.log("GLOBAL", "AUTH_LOGIN", f"Logged in with token to {host}")
        return True

    def switch_account(self, user: str, host: str = "github.com") -> bool:
        """Switch active account."""
        args = ["auth", "switch", "--user", user, "--hostname", host]
        self.executor.run_text(args)
        AuditLogger.log("GLOBAL", "AUTH_SWITCH", f"Switched account to {user} on {host}")
        return True

    def logout(self, host: str = "github.com", user: Optional[str] = None) -> bool:
        """Log out of GitHub."""
        args = ["auth", "logout", "--hostname", host, "-y"]
        if user:
            args.extend(["--user", user])
        self.executor.run_text(args)
        AuditLogger.log("GLOBAL", "AUTH_LOGOUT", f"Logged out of {host}")
        return True
