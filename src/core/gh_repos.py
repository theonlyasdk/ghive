"""GitHub repository operations via gh repo."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .audit_logger import AuditLogger
from .gh_executor import GHExecutor

REPO_LIST_FIELDS = [
    "name",
    "nameWithOwner",
    "description",
    "isPrivate",
    "isFork",
    "stargazerCount",
    "forkCount",
    "updatedAt",
    "url",
]

REPO_VIEW_FIELDS = [
    "name",
    "nameWithOwner",
    "description",
    "url",
    "sshUrl",
    "isPrivate",
    "isFork",
    "stargazerCount",
    "forkCount",
    "watchers",
    "defaultBranchRef",
    "licenseInfo",
    "languages",
    "createdAt",
    "updatedAt",
    "homepageUrl",
    "parent",
]


class GHRepos:
    """Handles GitHub repository operations."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_repos(
        self,
        owner: Optional[str] = None,
        limit: int = 30,
        visibility: Optional[str] = None,
        fork: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List repositories for user or organization."""
        args = ["repo", "list"]
        if owner:
            args.append(owner)

        args.extend(["--limit", str(limit), "--json", ",".join(REPO_LIST_FIELDS)])

        if visibility in ("public", "private", "internal"):
            args.extend(["--visibility", visibility])

        if fork is True:
            args.append("--fork")
        elif fork is False:
            args.append("--source")

        data = self.executor.run_json(args)
        return data if isinstance(data, list) else []

    def view_repo(self, name_with_owner: str) -> Dict[str, Any]:
        """Get rich metadata for a repository."""
        args = ["repo", "view", name_with_owner, "--json", ",".join(REPO_VIEW_FIELDS)]
        data = self.executor.run_json(args)
        return data if isinstance(data, dict) else {}

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        init_readme: bool = True,
        gitignore: Optional[str] = None,
        license: Optional[str] = None,
        clone_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Create a new GitHub repository."""
        args = ["repo", "create", name]
        if private:
            args.append("--private")
        else:
            args.append("--public")

        if description:
            args.extend(["--description", description])

        if init_readme:
            args.append("--add-readme")

        if gitignore:
            args.extend(["--gitignore", gitignore])

        if license:
            args.extend(["--license", license])

        if clone_path:
            args.extend(["--clone"])
            output = self.executor.run_text(args, cwd=str(clone_path))
        else:
            output = self.executor.run_text(args)

        AuditLogger.log(name, "REPO_CREATE", f"Created repo (private={private})")
        return output

    def delete_repo(self, name_with_owner: str) -> bool:
        """Delete a GitHub repository permanently."""
        args = ["repo", "delete", name_with_owner, "--yes"]
        self.executor.run_text(args)
        AuditLogger.log(name_with_owner, "REPO_DELETE", "Permanently deleted repository")
        return True

    def clone_repo(
        self,
        name_with_owner: str,
        destination_dir: Union[str, Path],
        target_name: Optional[str] = None,
    ) -> str:
        """Clone repository to a local directory."""
        dest = Path(destination_dir)
        dest.mkdir(parents=True, exist_ok=True)

        args = ["repo", "clone", name_with_owner]
        if target_name:
            args.append(target_name)

        output = self.executor.run_text(args, cwd=str(dest), timeout=180)
        AuditLogger.log(name_with_owner, "REPO_CLONE", f"Cloned to {dest}")
        return output

    def sync_repo(self, name_with_owner: str, branch: Optional[str] = None) -> str:
        """Sync a fork with its upstream repository."""
        args = ["repo", "sync", name_with_owner]
        if branch:
            args.extend(["--branch", branch])
        output = self.executor.run_text(args)
        AuditLogger.log(name_with_owner, "REPO_SYNC", f"Synced repository branch {branch or 'default'}")
        return output

    def change_visibility(self, name_with_owner: str, visibility: str) -> str:
        """Change repository visibility ('public' or 'private')."""
        args = [
            "repo",
            "edit",
            name_with_owner,
            "--visibility",
            visibility.lower(),
            "--accept-visibility-change-consequences",
        ]
        output = self.executor.run_text(args)
        AuditLogger.log(name_with_owner, "REPO_VISIBILITY", f"Changed visibility to {visibility}")
        return output
