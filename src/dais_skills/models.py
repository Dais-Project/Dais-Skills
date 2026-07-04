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
class ScanResult:
    """Represents a discovered skill candidate from tree scanning."""
    repo_path: str


@dataclass
class TreeEntry:
    """Represents a single entry in a provider-neutral repository tree."""
    path: str
    kind: str  # "file" or "directory"
    size: Optional[int] = None


@dataclass
class Tree:
    """Represents a provider-neutral repository tree."""
    ref: str
    entries: list[TreeEntry]
