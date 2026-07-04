"""Main entry point for scanning repositories for skills."""

from typing import Optional, Callable
from urllib.parse import urlparse
from ..models import Skill
from .github_adapter import scan_github_repo


async def scan_repo(
    source: str,
    ref: Optional[str] = None,
    get_token: Optional[Callable[[], Optional[str]]] = None,
    include_internal: bool = False,
) -> list[Skill]:
    """
    Scan a repository for skills.

    This is the main entry point for the dais-skills package. It:
    1. Validates the source URL
    2. Routes to the appropriate adapter based on the URL scheme
    3. Returns discovered skills

    Args:
        source: Repository URL. Must be a complete URL starting with http:// or https://
            Supported formats:
            - https://github.com/owner/repo
            - https://github.com/owner/repo/tree/branch
            - https://github.com/owner/repo/tree/branch/path
        ref: Optional git ref (branch/tag/commit) to scan
        get_token: Optional callback to get authentication token when needed
        include_internal: Whether to include internal skills (default: False)

    Returns:
        List of Skill objects discovered in the repository

    Raises:
        ValueError: If the source is not a valid URL or unsupported

    Examples:
        >>> skills = await scan_repo("https://github.com/vercel-labs/agent-skills")
        >>> skills = await scan_repo("https://github.com/owner/repo")
    """
    source = source.strip()

    # Validate that source is a complete URL
    if not source.startswith(("http://", "https://")):
        raise ValueError(
            f"Invalid source: '{source}'. "
            "Source must be a complete URL starting with http:// or https://"
        )

    # Parse URL and route to appropriate adapter
    parsed = urlparse(source)

    if parsed.hostname == "github.com":
        return await scan_github_repo(source, ref, get_token, include_internal)

    raise ValueError(
        f"Unsupported source host: '{parsed.hostname}'. "
        "Currently only github.com is supported."
    )
