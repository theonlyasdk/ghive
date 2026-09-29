"""GitHub Actions workflow runs management via gh run."""

from typing import Any, Dict, List, Optional

from .audit_logger import AuditLogger
from .gh_executor import GHExecutor

RUN_LIST_FIELDS = [
    "databaseId",
    "name",
    "status",
    "conclusion",
    "workflowName",
    "headBranch",
    "event",
    "createdAt",
    "url",
]

RUN_VIEW_FIELDS = [
    "databaseId",
    "name",
    "status",
    "conclusion",
    "workflowName",
    "headBranch",
    "headSha",
    "event",
    "jobs",
    "createdAt",
    "updatedAt",
    "url",
]


class GHRuns:
    """Handles GitHub Actions workflow runs."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_runs(
        self,
        repo: str,
        limit: int = 30,
        workflow: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List workflow runs for a repository."""
        args = ["run", "list", "--repo", repo, "--limit", str(limit)]
        args.extend(["--json", ",".join(RUN_LIST_FIELDS)])

        if workflow:
            args.extend(["--workflow", workflow])

        if status:
            args.extend(["--status", status])

        data = self.executor.run_json(args)
        return data if isinstance(data, list) else []

    def view_run(self, repo: str, run_id: Any) -> Dict[str, Any]:
        """Get details for a specific workflow run."""
        args = [
            "run",
            "view",
            str(run_id),
            "--repo",
            repo,
            "--json",
            ",".join(RUN_VIEW_FIELDS),
        ]
        data = self.executor.run_json(args)
        return data if isinstance(data, dict) else {}

    def get_run_log(self, repo: str, run_id: Any) -> str:
        """Fetch the execution log of a workflow run."""
        args = ["run", "view", str(run_id), "--repo", repo, "--log"]
        return self.executor.run_text(args, timeout=90)

    def rerun(self, repo: str, run_id: Any, failed_only: bool = False) -> str:
        """Rerun a workflow."""
        args = ["run", "rerun", str(run_id), "--repo", repo]
        if failed_only:
            args.append("--failed")
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "RUN_RERUN", f"Reran run #{run_id} (failed_only={failed_only})")
        return output

    def cancel(self, repo: str, run_id: Any) -> str:
        """Cancel an in-progress workflow run."""
        args = ["run", "cancel", str(run_id), "--repo", repo]
        output = self.executor.run_text(args)
        AuditLogger.log(repo, "RUN_CANCEL", f"Cancelled run #{run_id}")
        return output
