"""GitHub issue operations via gh issue."""

from typing import Any, Dict, List, Optional

from .audit_logger import AuditLogger
from .gh_executor import GHExecutor

ISSUE_LIST_FIELDS = [
    "number",
    "title",
    "state",
    "author",
    "labels",
    "createdAt",
    "updatedAt",
    "url",
]

ISSUE_VIEW_FIELDS = [
    "number",
    "title",
    "state",
    "stateReason",
    "body",
    "author",
    "labels",
    "assignees",
    "createdAt",
    "updatedAt",
    "url",
    "comments",
]


class GHIssues:
    """Handles GitHub issue operations."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_issues(
        self,
        repo: str,
        state: str = "open",
        limit: int = 30,
        search: Optional[str] = None,
        label: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List issues for a repository."""
        args = ["issue", "list", "--repo", repo, "--limit", str(limit)]
        args.extend(["--json", ",".join(ISSUE_LIST_FIELDS)])

        if state in ("open", "closed", "all"):
            args.extend(["--state", state])

        if search:
            args.extend(["--search", search])

        if label:
            args.extend(["--label", label])

        if assignee:
            args.extend(["--assignee", assignee])

        data = self.executor.run_json(args)
        return data if isinstance(data, list) else []

    def view_issue(self, repo: str, number: int) -> Dict[str, Any]:
        """View full details of an issue including body and comments."""
        args = [
            "issue",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            ",".join(ISSUE_VIEW_FIELDS),
        ]
        data = self.executor.run_json(args)
        return data if isinstance(data, dict) else {}

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> str:
        """Create a new issue."""
        args = ["issue", "create", "--repo", repo, "--title", title, "--body", body]

        if labels:
            for lbl in labels:
                if lbl.strip():
                    args.extend(["--label", lbl.strip()])

        if assignees:
            for asn in assignees:
                if asn.strip():
                    args.extend(["--assignee", asn.strip()])

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "ISSUE_CREATE", f"Created issue '{title}'")
        return output

    def close_issue(self, repo: str, number: int, reason: Optional[str] = None) -> str:
        """Close an existing issue."""
        args = ["issue", "close", str(number), "--repo", repo]
        if reason in ("completed", "not planned"):
            args.extend(["--reason", reason])

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "ISSUE_CLOSE", f"Closed issue #{number} (reason: {reason})")
        return output

    def reopen_issue(self, repo: str, number: int) -> str:
        """Reopen a closed issue."""
        args = ["issue", "reopen", str(number), "--repo", repo]
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "ISSUE_REOPEN", f"Reopened issue #{number}")
        return output

    def comment_issue(self, repo: str, number: int, body: str) -> str:
        """Add a comment to an issue."""
        args = ["issue", "comment", str(number), "--repo", repo, "--body", body]
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "ISSUE_COMMENT", f"Commented on issue #{number}")
        return output
