"""GitHub source parsing utilities."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubSource:
    """Parsed GitHub source input."""
    owner_repo: str
    url: str
    ref: Optional[str] = None
    subpath: Optional[str] = None
    skill_filter: Optional[str] = None


def sanitize_subpath(subpath: str) -> str:
    """
    Sanitizes a subpath to prevent path traversal attacks.
    Rejects subpaths containing ".." segments that could escape the repository root.
    """
    normalized = subpath.replace("\\", "/")
    segments = normalized.split("/")
    for segment in segments:
        if segment == "..":
            raise ValueError(
                f'Unsafe subpath: "{subpath}" contains path traversal segments. '
                'Subpaths must not contain ".." components.'
            )
    return subpath


def parse_github_source(input_str: str) -> GitHubSource:
    """Parse a GitHub source string into structured format."""
    input_str = input_str.strip()

    if input_str.startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse as _urlparse
            parsed_url = _urlparse(input_str)
            if parsed_url.hostname in ("github.com",):
                input_str = f"github.com{parsed_url.path}"
                if parsed_url.query:
                    input_str += f"?{parsed_url.query}"
                if parsed_url.fragment:
                    input_str += f"#{parsed_url.fragment}"
        except Exception:
            pass

    fragment_ref = None
    fragment_skill_filter = None
    if "#" in input_str:
        base, fragment = input_str.split("#", 1)
        if "@" in fragment:
            ref_part, skill_part = fragment.split("@", 1)
            fragment_ref = ref_part if ref_part else None
            fragment_skill_filter = skill_part if skill_part else None
        else:
            fragment_ref = fragment
        input_str = base

    match = re.match(r"github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)", input_str)
    if match:
        owner, repo, ref, subpath = match.groups()
        owner_repo = f"{owner}/{repo}"
        return GitHubSource(
            owner_repo=owner_repo,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=ref or fragment_ref,
            subpath=sanitize_subpath(subpath) if subpath else None,
            skill_filter=fragment_skill_filter,
        )

    match = re.match(r"github\.com/([^/]+)/([^/]+)/tree/([^/]+)$", input_str)
    if match:
        owner, repo, ref = match.groups()
        owner_repo = f"{owner}/{repo}"
        return GitHubSource(
            owner_repo=owner_repo,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=ref or fragment_ref,
            skill_filter=fragment_skill_filter,
        )

    match = re.match(r"github\.com/([^/]+)/([^/@]+)(?:@([^/]+))?", input_str)
    if match:
        owner, repo, skill_filter = match.groups()
        repo = repo.replace(".git", "")
        owner_repo = f"{owner}/{repo}"
        return GitHubSource(
            owner_repo=owner_repo,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=fragment_ref,
            skill_filter=fragment_skill_filter or skill_filter,
        )

    match = re.match(r"^([^/]+)/([^/@]+)@(.+)$", input_str)
    if match and not input_str.startswith(".") and not input_str.startswith("/"):
        owner, repo, skill_filter = match.groups()
        owner_repo = f"{owner}/{repo}"
        return GitHubSource(
            owner_repo=owner_repo,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=fragment_ref,
            skill_filter=fragment_skill_filter or skill_filter,
        )

    match = re.match(r"^([^/]+)/([^/]+)(?:/(.+?))?/?$", input_str)
    if match and not input_str.startswith(".") and not input_str.startswith("/") and ":" not in input_str:
        owner, repo, subpath = match.groups()
        owner_repo = f"{owner}/{repo}"
        return GitHubSource(
            owner_repo=owner_repo,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=fragment_ref,
            subpath=sanitize_subpath(subpath) if subpath else None,
            skill_filter=fragment_skill_filter,
        )

    raise ValueError(f"Unable to parse GitHub source: {input_str}")
