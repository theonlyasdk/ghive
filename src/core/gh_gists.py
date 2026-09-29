"""GitHub Gist operations via gh api and gh gist."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .audit_logger import AuditLogger
from .gh_executor import GHExecutor


class GHGists:
    """Handles GitHub Gist operations."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_gists(self, limit: int = 30, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List user gists."""
        endpoint = f"/gists?per_page={min(limit, 100)}"
        raw_data = self.executor.run_json(["api", endpoint])
        if not isinstance(raw_data, list):
            return []

        gists = []
        for item in raw_data:
            is_public = item.get("public", False)
            if visibility == "public" and not is_public:
                continue
            if visibility == "secret" and is_public:
                continue

            file_names = list(item.get("files", {}).keys())
            gists.append(
                {
                    "id": item.get("id", ""),
                    "description": item.get("description", "") or "(No description)",
                    "public": is_public,
                    "files": file_names,
                    "file_count": len(file_names),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                    "url": item.get("html_url", ""),
                }
            )

        return gists[:limit]

    def view_gist(self, gist_id: str) -> Dict[str, Any]:
        """Fetch full details and file contents for a gist."""
        data = self.executor.run_json(["api", f"/gists/{gist_id}"])
        return data if isinstance(data, dict) else {}

    def create_gist(
        self,
        filename: str,
        content: str,
        description: str = "",
        public: bool = False,
    ) -> str:
        """Create a new gist from file content."""
        # Using temporary file with gh gist create is safest across OS platforms
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / (filename if filename.strip() else "gistfile1.txt")
            file_path.write_text(content, encoding="utf-8")

            args = ["gist", "create", str(file_path)]
            if description:
                args.extend(["-d", description])
            if public:
                args.append("--public")

            output = self.executor.run_text(args)
            AuditLogger.log(f"gist:{filename}", "GIST_CREATE", f"Created gist (public={public})")
            return output

    def delete_gist(self, gist_id: str) -> bool:
        """Delete a gist."""
        args = ["gist", "delete", gist_id]
        self.executor.run_text(args)
        AuditLogger.log(f"gist:{gist_id}", "GIST_DELETE", "Deleted gist")
        return True

    def clone_gist(self, gist_id: str, destination_dir: Union[str, Path]) -> str:
        """Clone a gist locally."""
        dest = Path(destination_dir)
        dest.mkdir(parents=True, exist_ok=True)
        args = ["gist", "clone", gist_id]
        output = self.executor.run_text(args, cwd=str(dest))
        AuditLogger.log(f"gist:{gist_id}", "GIST_CLONE", f"Cloned to {dest}")
        return output

    def update_description(self, gist_id: str, description: str) -> Dict[str, Any]:
        """Update a gist description."""
        payload = {"description": description}
        args = ["api", "-X", "PATCH", f"/gists/{gist_id}", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        AuditLogger.log(f"gist:{gist_id}", "GIST_UPDATE_DESC", f"Updated description: {description}")
        return data if isinstance(data, dict) else {}

    def add_file(self, gist_id: str, filename: str, content: str = " ") -> Dict[str, Any]:
        """Add a new page/file to an existing gist."""
        payload = {"files": {filename: {"content": content or " "}}}
        args = ["api", "-X", "PATCH", f"/gists/{gist_id}", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        AuditLogger.log(f"gist:{gist_id}", "GIST_ADD_FILE", f"Added file: {filename}")
        return data if isinstance(data, dict) else {}

    def rename_file(self, gist_id: str, old_filename: str, new_filename: str) -> Dict[str, Any]:
        """Rename an existing page/file in a gist."""
        payload = {"files": {old_filename: {"filename": new_filename}}}
        args = ["api", "-X", "PATCH", f"/gists/{gist_id}", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        AuditLogger.log(f"gist:{gist_id}", "GIST_RENAME_FILE", f"Renamed {old_filename} -> {new_filename}")
        return data if isinstance(data, dict) else {}

    def delete_file(self, gist_id: str, filename: str) -> Dict[str, Any]:
        """Delete a page/file from a gist."""
        payload = {"files": {filename: None}}
        args = ["api", "-X", "PATCH", f"/gists/{gist_id}", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        AuditLogger.log(f"gist:{gist_id}", "GIST_DELETE_FILE", f"Deleted file: {filename}")
        return data if isinstance(data, dict) else {}

    def update_file_content(self, gist_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Save updated content for an existing page/file in a gist."""
        payload = {"files": {filename: {"content": content}}}
        args = ["api", "-X", "PATCH", f"/gists/{gist_id}", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        AuditLogger.log(f"gist:{gist_id}", "GIST_UPDATE_CONTENT", f"Updated file: {filename}")
        return data if isinstance(data, dict) else {}

    def create_gist_multi(
        self,
        files: Dict[str, str],
        description: str = "",
        public: bool = False,
    ) -> str:
        """Create a new gist with multiple files."""
        payload = {
            "description": description,
            "public": public,
            "files": {fname: {"content": content or " "} for fname, content in files.items()},
        }
        args = ["api", "-X", "POST", "/gists", "--input", "-"]
        data = self.executor.run_json(args, stdin_input=json.dumps(payload))
        new_id = data.get("id", "") if isinstance(data, dict) else ""
        AuditLogger.log(f"gist:{description}", "GIST_CREATE_MULTI", f"Created gist {new_id} (public={public})")
        return new_id

    def change_visibility(self, gist_id: str, to_public: bool) -> str:
        """Change gist visibility by creating a new gist with desired visibility and deleting the old one."""
        old_data = self.view_gist(gist_id)
        files = {}
        for fname, fobj in old_data.get("files", {}).items():
            files[fname] = fobj.get("content", " ")
        if not files:
            files["gistfile1.txt"] = " "

        desc = old_data.get("description", "")
        new_id = self.create_gist_multi(files, description=desc, public=to_public)
        if new_id:
            try:
                self.delete_gist(gist_id)
            except Exception:
                pass
            AuditLogger.log(f"gist:{gist_id}", "GIST_CHANGE_VISIBILITY", f"Converted {gist_id} -> {new_id} (public={to_public})")
        return new_id

