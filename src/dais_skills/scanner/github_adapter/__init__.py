"""GitHub adapter for scanning repositories for skills."""

import asyncio
import httpx
from typing import Optional, Callable
from ...models import Skill
from ...skill_discovery import (
    scan_tree_for_skills,
    parse_skill_from_content,
    to_skill_slug,
)
from .api import fetch_repo_tree
from .source import parse_github_source


async def fetch_skill_md_content(
    owner_repo: str,
    ref: str,
    skill_md_path: str,
) -> Optional[str]:
    """Fetch a single SKILL.md from raw.githubusercontent.com."""
    url = f"https://raw.githubusercontent.com/{owner_repo}/{ref}/{skill_md_path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
            return None
    except Exception:
        return None


async def scan_github_repo(
    source: str,
    ref: Optional[str] = None,
    get_token: Optional[Callable[[], Optional[str]]] = None,
    include_internal: bool = False,
) -> list[Skill]:
    """
    Scan a GitHub repository for skills.

    Args:
        source: Repository source string. Supports:
            - owner/repo
            - owner/repo@skill-name
            - owner/repo/path/to/subdir
            - https://github.com/owner/repo
            - https://github.com/owner/repo/tree/branch
            - https://github.com/owner/repo/tree/branch/path
        ref: Optional git ref (branch/tag/commit) to scan
        get_token: Optional callback to get GitHub token when rate limited
        include_internal: Whether to include internal skills (default: False)

    Returns:
        List of Skill objects discovered in the repository

    Raises:
        ValueError: If the source string cannot be parsed
    """
    parsed = parse_github_source(source)

    if ref:
        parsed.ref = ref

    tree = await fetch_repo_tree(
        parsed.owner_repo,
        ref=parsed.ref,
        get_token=get_token,
    )

    if not tree:
        return []

    scan_results = scan_tree_for_skills(tree, parsed.subpath)

    if not scan_results:
        return []

    if parsed.skill_filter:
        filter_slug = to_skill_slug(parsed.skill_filter)
        filtered_results = [
            result for result in scan_results
            if len(result.repo_path.split("/")) >= 2
            and to_skill_slug(result.repo_path.split("/")[-2]) == filter_slug
        ]
        if filtered_results:
            scan_results = filtered_results

    fetch_tasks = [
        fetch_skill_md_content(parsed.owner_repo, tree.ref, result.repo_path)
        for result in scan_results
    ]

    contents = await asyncio.gather(*fetch_tasks)

    skills = []
    for result, content in zip(scan_results, contents):
        if not content:
            continue

        skill = parse_skill_from_content(
            content,
            repo_path=result.repo_path,
            include_internal=include_internal,
        )

        if skill:
            skills.append(skill)

    if parsed.skill_filter and len(skills) > 1:
        filter_slug = to_skill_slug(parsed.skill_filter)
        filtered_skills = [
            s for s in skills
            if to_skill_slug(s.name) == filter_slug
        ]
        if filtered_skills:
            skills = filtered_skills

    return skills
