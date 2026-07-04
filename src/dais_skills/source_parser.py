"""Parse source string into structured format."""

import re
from urllib.parse import urlparse
from .models import ParsedSource


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
                "Subpaths must not contain \"..\" components."
            )
    return subpath


def parse_source(input_str: str) -> ParsedSource:
    """
    Parse a source string into a structured format.

    Supports:
    - owner/repo
    - owner/repo@skill-name
    - owner/repo/path/to/subdir
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/branch
    - https://github.com/owner/repo/tree/branch/path

    Args:
        input_str: Source string to parse

    Returns:
        ParsedSource object with parsed components

    Raises:
        ValueError: If the input cannot be parsed as a GitHub source
    """
    input_str = input_str.strip()

    # Normalize https?://github.com/... to github.com/... for uniform regex matching
    if input_str.startswith(("http://", "https://")):
        try:
            from urllib.parse import urlparse as _urlparse
            parsed_url = _urlparse(input_str)
            if parsed_url.hostname in ("github.com",):
                # Reconstruct as "github.com/<path>"
                input_str = f"github.com{parsed_url.path}"
                if parsed_url.query:
                    input_str += f"?{parsed_url.query}"
                if parsed_url.fragment:
                    input_str += f"#{parsed_url.fragment}"
        except Exception:
            pass

    # Handle fragment (#) for ref and skill filter
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

    # GitHub URL with path: https://github.com/owner/repo/tree/branch/path/to/skill
    match = re.match(r"github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)", input_str)
    if match:
        owner, repo, ref, subpath = match.groups()
        owner_repo = f"{owner}/{repo}"
        return ParsedSource(
            type="github",
            url=f"https://github.com/{owner}/{repo}.git",
            owner_repo=owner_repo,
            ref=ref or fragment_ref,
            subpath=sanitize_subpath(subpath) if subpath else None,
        )

    # GitHub URL with branch only: https://github.com/owner/repo/tree/branch
    match = re.match(r"github\.com/([^/]+)/([^/]+)/tree/([^/]+)$", input_str)
    if match:
        owner, repo, ref = match.groups()
        owner_repo = f"{owner}/{repo}"
        return ParsedSource(
            type="github",
            url=f"https://github.com/{owner}/{repo}.git",
            owner_repo=owner_repo,
            ref=ref or fragment_ref,
        )

    # GitHub URL: https://github.com/owner/repo
    match = re.match(r"github\.com/([^/]+)/([^/]+)", input_str)
    if match:
        owner, repo = match.groups()
        repo = repo.replace(".git", "")
        owner_repo = f"{owner}/{repo}"
        return ParsedSource(
            type="github",
            url=f"https://github.com/{owner}/{repo}.git",
            owner_repo=owner_repo,
            ref=fragment_ref,
        )

    # GitHub shorthand with @skill: owner/repo@skill-name
    match = re.match(r"^([^/]+)/([^/@]+)@(.+)$", input_str)
    if match and not input_str.startswith(".") and not input_str.startswith("/"):
        owner, repo, skill_filter = match.groups()
        owner_repo = f"{owner}/{repo}"
        return ParsedSource(
            type="github",
            url=f"https://github.com/{owner}/{repo}.git",
            owner_repo=owner_repo,
            ref=fragment_ref,
            skill_filter=fragment_skill_filter or skill_filter,
        )

    # GitHub shorthand: owner/repo or owner/repo/path/to/skill
    match = re.match(r"^([^/]+)/([^/]+)(?:/(.+?))?/?$", input_str)
    if match and not input_str.startswith(".") and not input_str.startswith("/") and ":" not in input_str:
        owner, repo, subpath = match.groups()
        owner_repo = f"{owner}/{repo}"
        return ParsedSource(
            type="github",
            url=f"https://github.com/{owner}/{repo}.git",
            owner_repo=owner_repo,
            ref=fragment_ref,
            subpath=sanitize_subpath(subpath) if subpath else None,
            skill_filter=fragment_skill_filter,
        )

    raise ValueError(f"Unable to parse source: {input_str}")
