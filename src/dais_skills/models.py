"""Data models for skill scanning."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Skill:
    """Represents a discovered skill."""
    name: str
    description: str
    repo_path: str  # Path within the repo (e.g., "skills/react/SKILL.md")
    raw_content: str
    metadata: Optional[dict] = None


@dataclass
class TreeEntry:
    """Represents a single entry in a GitHub tree."""
    path: str
    type: str  # "blob" or "tree"
    sha: str
    size: Optional[int] = None


@dataclass
class RepoTree:
    """Represents a GitHub repository tree."""
    sha: str
    branch: str
    tree: list[TreeEntry]


@dataclass
class ParsedSource:
    """Represents a parsed source input."""
    type: str  # "github", "gitlab", "git", "local"
    url: str
    owner_repo: str  # e.g., "vercel-labs/agent-skills"
    ref: Optional[str] = None
    subpath: Optional[str] = None
    skill_filter: Optional[str] = None
