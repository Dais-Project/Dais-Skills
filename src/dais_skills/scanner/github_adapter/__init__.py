"""GitHub adapter for scanning repositories for skills."""

import asyncio
from typing import Optional, Callable
from ...models import Skill
from ...source_parser import parse_source
from .api import fetch_repo_tree
from ...skill_discovery import (
    find_skill_md_paths,
    fetch_skill_md_content,
    parse_skill_from_content,
    to_skill_slug,
)


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
            - owner/repo@skill-name (filters to specific skill)
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
    # 1. Parse the source string
    parsed = parse_source(source)

    # Override ref if provided as argument
    if ref:
        parsed.ref = ref

    # 2. Fetch the repo tree
    tree = await fetch_repo_tree(
        parsed.owner_repo,
        ref=parsed.ref,
        get_token=get_token,
    )

    if not tree:
        return []

    # 3. Discover SKILL.md paths in the tree
    skill_md_paths = find_skill_md_paths(tree, parsed.subpath)

    if not skill_md_paths:
        return []

    # 4. If a skill filter is set, try to narrow down by folder name first
    if parsed.skill_filter:
        filter_slug = to_skill_slug(parsed.skill_filter)
        filtered_paths = [
            p for p in skill_md_paths
            if len(p.split("/")) >= 2 and to_skill_slug(p.split("/")[-2]) == filter_slug
        ]
        if filtered_paths:
            skill_md_paths = filtered_paths

    # 5. Fetch SKILL.md content in parallel
    fetch_tasks = [
        fetch_skill_md_content(parsed.owner_repo, tree.branch, md_path)
        for md_path in skill_md_paths
    ]

    contents = await asyncio.gather(*fetch_tasks)

    # 6. Parse frontmatter and build Skill objects
    skills = []
    for md_path, content in zip(skill_md_paths, contents):
        if not content:
            continue

        skill = parse_skill_from_content(
            content,
            repo_path=md_path,
            include_internal=include_internal,
        )

        if skill:
            skills.append(skill)

    # 7. Apply skill filter by name if not already filtered by folder name
    if parsed.skill_filter and len(skills) > 1:
        filter_slug = to_skill_slug(parsed.skill_filter)
        filtered_skills = [
            s for s in skills
            if to_skill_slug(s.name) == filter_slug
        ]
        if filtered_skills:
            skills = filtered_skills

    return skills
