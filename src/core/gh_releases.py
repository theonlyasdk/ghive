"""GitHub release operations via gh release and GitHub REST API."""

import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .audit_logger import AuditLogger
from .exceptions import GHCLIError
from .gh_executor import GHExecutor

RELEASE_LIST_FIELDS = [
    "tagName",
    "name",
    "isDraft",
    "isPrerelease",
    "isLatest",
    "publishedAt",
    "createdAt",
]

RELEASE_VIEW_FIELDS = [
    "tagName",
    "name",
    "body",
    "isDraft",
    "isPrerelease",
    "publishedAt",
    "createdAt",
    "url",
    "uploadUrl",
    "assets",
    "author",
]


class GHReleases:
    """Handles GitHub release and asset operations."""

    def __init__(self, executor: GHExecutor):
        self.executor = executor

    def list_releases(self, repo: str, limit: int = 30) -> List[Dict[str, Any]]:
        """List releases for a repository."""
        args = ["release", "list", "--repo", repo, "--limit", str(limit), "--json", ",".join(RELEASE_LIST_FIELDS)]
        data = self.executor.run_json(args)
        return data if isinstance(data, list) else []

    def view_release(self, repo: str, tag: str) -> Dict[str, Any]:
        """View full details and assets for a release tag."""
        args = ["release", "view", tag, "--repo", repo, "--json", ",".join(RELEASE_VIEW_FIELDS)]
        data = self.executor.run_json(args)
        return data if isinstance(data, dict) else {}

    def create_release(
        self,
        repo: str,
        tag: str,
        title: str = "",
        notes: str = "",
        draft: bool = False,
        prerelease: bool = False,
        target: Optional[str] = None,
    ) -> str:
        """Create a new release."""
        args = ["release", "create", tag, "--repo", repo]
        if title:
            args.extend(["--title", title])
        if notes:
            args.extend(["--notes", notes])
        if draft:
            args.append("--draft")
        if prerelease:
            args.append("--prerelease")
        if target:
            args.extend(["--target", target])

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "RELEASE_CREATE", f"Created release {tag} (draft={draft})")
        return output

    def edit_release(
        self,
        repo: str,
        tag: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        draft: Optional[bool] = None,
        prerelease: Optional[bool] = None,
    ) -> str:
        """Edit release title, notes, or flags."""
        args = ["release", "edit", tag, "--repo", repo]
        if title is not None:
            args.extend(["--title", title])
        if notes is not None:
            args.extend(["--notes", notes])
        if draft is not None:
            args.append(f"--draft={str(draft).lower()}")
        if prerelease is not None:
            args.append(f"--prerelease={str(prerelease).lower()}")

        output = self.executor.run_text(args)
        AuditLogger.log(repo, "RELEASE_EDIT", f"Edited release {tag}")
        return output

    def delete_release(self, repo: str, tag: str) -> bool:
        """Delete a release."""
        args = ["release", "delete", tag, "--repo", repo, "-y"]
        self.executor.run_text(args)
        AuditLogger.log(repo, "RELEASE_DELETE", f"Deleted release {tag}")
        return True

    def delete_asset(self, repo: str, tag: str, asset_name: str) -> bool:
        """Delete an asset from a release."""
        args = ["release", "delete-asset", tag, asset_name, "--repo", repo, "-y"]
        self.executor.run_text(args)
        AuditLogger.log(repo, "RELEASE_DELETE_ASSET", f"Deleted asset {asset_name} from {tag}")
        return True

    def download_asset(self, repo: str, tag: str, asset_name: str, dest_dir: Union[str, Path]) -> str:
        """Download a specific asset file."""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        args = ["release", "download", tag, "--repo", repo, "-p", asset_name, "-D", str(dest), "--clobber"]
        output = self.executor.run_text(args, timeout=300)
        AuditLogger.log(repo, "RELEASE_DOWNLOAD_ASSET", f"Downloaded {asset_name} to {dest}")
        return output

    def upload_asset_streaming(
        self,
        repo: str,
        tag: str,
        file_path: Union[str, Path],
        progress_callback: Optional[Callable[[int, int, float, float, float], None]] = None,
        cancel_event: Optional[Any] = None,
    ) -> bool:
        """Upload an asset with streaming progress (live rate, acceleration, ETA)."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Asset file not found: {path}")

        file_size = path.stat().st_size
        if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB GitHub limit
            raise ValueError("File exceeds GitHub's 2GB release asset limit.")

        token = ""
        try:
            token = self.executor.run_text(["auth", "token"]).strip()
        except Exception:
            token = ""

        # Fetch release upload URL if token available
        upload_url = None
        if token:
            try:
                rel_data = self.view_release(repo, tag)
                upload_url = rel_data.get("uploadUrl")
            except Exception:
                upload_url = None

        if token and upload_url:
            self._upload_via_api(upload_url, path, file_size, token, progress_callback, cancel_event)
        else:
            # Fallback to gh release upload
            args = ["release", "upload", tag, str(path), "--repo", repo, "--clobber"]
            self.executor.run_text(args, timeout=600)

        AuditLogger.log(repo, "RELEASE_UPLOAD_ASSET", f"Uploaded {path.name} ({file_size} bytes) to {tag}")
        return True

    def _upload_via_api(
        self,
        upload_url_template: str,
        path: Path,
        file_size: int,
        token: str,
        progress_callback: Optional[Callable[[int, int, float, float, float], None]],
        cancel_event: Optional[Any],
    ) -> None:
        """Upload directly via uploads.github.com with live metrics."""
        base_url = upload_url_template.split("{")[0]
        query_params = urllib.parse.urlencode({"name": path.name})
        full_url = f"{base_url}?{query_params}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),
            "User-Agent": "ghive-gui-client",
        }

        chunk_size = 64 * 1024  # 64 KB chunks
        uploaded_bytes = 0
        last_time = time.time()
        start_time = last_time
        last_bytes = 0
        prev_rate = 0.0

        class StreamingBody:
            def __init__(self, file_obj):
                self.file_obj = file_obj

            def read(self, amt=-1):
                nonlocal uploaded_bytes, last_time, last_bytes, prev_rate
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError("Upload cancelled by user.")

                chunk = self.file_obj.read(chunk_size if amt == -1 else amt)
                if chunk:
                    uploaded_bytes += len(chunk)
                    now = time.time()
                    dt = now - last_time
                    if dt >= 0.25 or uploaded_bytes == file_size:
                        bytes_diff = uploaded_bytes - last_bytes
                        current_rate = bytes_diff / dt if dt > 0 else 0.0
                        accel = (current_rate - prev_rate) / dt if dt > 0 else 0.0
                        rem_bytes = max(0, file_size - uploaded_bytes)
                        eta = (rem_bytes / current_rate) if current_rate > 0 else 0.0

                        prev_rate = current_rate
                        last_time = now
                        last_bytes = uploaded_bytes

                        if progress_callback:
                            progress_callback(uploaded_bytes, file_size, current_rate, accel, eta)
                return chunk

            def __len__(self):
                return file_size

        with open(path, "rb") as f:
            stream_body = StreamingBody(f)
            req = urllib.request.Request(full_url, data=stream_body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    if resp.status not in (200, 201):
                        raise GHCLIError(f"Upload failed with HTTP status {resp.status}")
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")
                raise GHCLIError(f"HTTP {exc.code} upload error: {err_body}")
