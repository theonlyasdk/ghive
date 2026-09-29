"""GitHub pull request operations via gh pr."""

from typing import Any, Dict, List, Optional

from .audit_logger import AuditLogger
from .gh_executor import GHExecutor

PR_LIST_FIELDS = [
    "number",
    "title",
    "state",
    "author",
    "headRefName",
    "baseRefName",
    "isDraft",
    "createdAt",
    "updatedAt",
    "url",
]

PR_VIEW_FIELDS = [
    "number",
    "title",
    "state",
    "body",
    "author",
    "headRefName",
    "baseRefName",
    "isDraft",
    "mergeable",
    "labels",
    "assignees",
    "reviewRequests",
    "statusCheckRollup",
    "createdAt",
    "updatedAt",
    "url",
    "comments",
]


class GHPRs:
    """Handles GitHub pull request operations."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_prs(
        self,
        repo: str,
        state: str = "open",
        limit: int = 30,
        search: Optional[str] = None,
        base: Optional[str] = None,
        head: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        args = ["pr", "list", "--repo", repo, "--limit", str(limit)]
        args.extend(["--json", ",".join(PR_LIST_FIELDS)])

        if state in ("open", "closed", "merged", "all"):
            args.extend(["--state", state])

        if search:
            args.extend(["--search", search])

        if base:
            args.extend(["--base", base])

        if head:
            args.extend(["--head", head])

        data = self.executor.run_json(args)
        return data if isinstance(data, list) else []

    def view_pr(self, repo: str, number: int) -> Dict[str, Any]:
        """View full details of a pull request."""
        args = [
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            ",".join(PR_VIEW_FIELDS),
        ]
        data = self.executor.run_json(args)
        return data if isinstance(data, dict) else {}

    def get_diff(self, repo: str, number: int) -> str:
        """Fetch unified diff for a pull request."""
        args = ["pr", "diff", str(number), "--repo", repo]
        return self.executor.run_text(args)

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str = "",
        base: Optional[str] = None,
        head: Optional[str] = None,
        draft: bool = False,
    ) -> str:
        """Create a new pull request."""
        args = ["pr", "create", "--repo", repo, "--title", title, "--body", body]
        if base:
            args.extend(["--base", base])
        if head:
            args.extend(["--head", head])
        if draft:
            args.append("--draft")

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "PR_CREATE", f"Created PR '{title}'")
        return output

    def close_pr(self, repo: str, number: int, delete_branch: bool = False) -> str:
        """Close a pull request."""
        args = ["pr", "close", str(number), "--repo", repo]
        if delete_branch:
            args.append("--delete-branch")
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "PR_CLOSE", f"Closed PR #{number} (delete_branch={delete_branch})")
        return output

    def reopen_pr(self, repo: str, number: int) -> str:
        """Reopen a closed pull request."""
        args = ["pr", "reopen", str(number), "--repo", repo]
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "PR_REOPEN", f"Reopened PR #{number}")
        return output

    def merge_pr(
        self,
        repo: str,
        number: int,
        method: str = "merge",
        delete_branch: bool = False,
        auto: bool = False,
    ) -> str:
        """Merge a pull request."""
        args = ["pr", "merge", str(number), "--repo", repo]
        if method == "squash":
            args.append("--squash")
        elif method == "rebase":
            args.append("--rebase")
        else:
            args.append("--merge")

        if delete_branch:
            args.append("--delete-branch")

        if auto:
            args.append("--auto")

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "PR_MERGE", f"Merged PR #{number} with {method}")
        return output

    def checkout_pr(self, repo: str, number: int) -> str:
        """Check out a PR locally in current working directory."""
        args = ["pr", "checkout", str(number), "--repo", repo]
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "PR_CHECKOUT", f"Checked out PR #{number}")
        return output
