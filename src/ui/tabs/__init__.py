"""Tab views for ghive main window."""

from .gists_tab import GistsTab
from .issues_tab import IssuesTab
from .prs_tab import PRsTab
from .repos_tab import ReposTab
from .runs_tab import RunsTab

__all__ = [
    "ReposTab",
    "IssuesTab",
    "PRsTab",
    "RunsTab",
    "GistsTab",
]
