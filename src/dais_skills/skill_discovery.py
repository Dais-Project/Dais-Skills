"""Skill discovery from provider-neutral repository trees."""

import frontmatter
from typing import Optional
from .models import Tree, Skill, ScanResult


# Known directories where SKILL.md files are commonly found
PRIORITY_PREFIXES = [
    "",
    "skills/",
    "skills/.curated/",
    "skills/.experimental/",
    "skills/.system/",
    ".agents/skills/",
    ".claude/skills/",
    ".cline/skills/",
    ".codebuddy/skills/",
    ".codex/skills/",
    ".commandcode/skills/",
    ".continue/skills/",
    ".github/skills/",
    ".goose/skills/",
    ".iflow/skills/",
    ".junie/skills/",
    ".kilocode/skills/",
    ".kiro/skills/",
    ".mux/skills/",
    ".neovate/skills/",
    ".opencode/skills/",
    ".openhands/skills/",
    ".pi/skills/",
    ".qoder/skills/",
    ".roo/skills/",
    ".trae/skills/",
    ".windsurf/skills/",
    ".zencoder/skills/",
]

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}


def find_skill_md_paths(tree: Tree, subpath: Optional[str] = None) -> list[str]:
    """
    Find all SKILL.md file paths in a repository tree.

    Args:
        tree: Provider-neutral repository tree
        subpath: Optional subpath to filter results

    Returns:
        List of SKILL.md file paths
    """
    all_skill_mds = [
        entry.path
        for entry in tree.entries
        if entry.kind == "file" and entry.path.lower().endswith("skill.md")
    ]

    prefix = (subpath + "/") if subpath and not subpath.endswith("/") else (subpath or "")
    filtered = [
        p for p in all_skill_mds
        if p.startswith(prefix) or p == prefix + "SKILL.md"
    ] if prefix else all_skill_mds

    if not filtered:
        return []

    priority_results = []
    seen = set()
    lower_skill_md_set = {p.lower() for p in filtered}

    for priority_prefix in PRIORITY_PREFIXES:
        full_prefix = prefix + priority_prefix
        is_container = priority_prefix != ""

        for skill_md in filtered:
            if not skill_md.startswith(full_prefix):
                continue

            rest = skill_md[len(full_prefix):]

            if rest.lower() == "skill.md":
                if skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)
                continue

            parts = rest.split("/")
            if len(parts) == 2 and parts[1].lower() == "skill.md":
                if skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)
                continue

            if (
                is_container
                and len(parts) == 3
                and parts[2].lower() == "skill.md"
                and parts[0] not in SKIP_DIRS
                and parts[1] not in SKIP_DIRS
            ):
                parent_skill_md = f"{full_prefix}{parts[0]}/SKILL.md".lower()
                if parent_skill_md not in lower_skill_md_set and skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)

    if priority_results:
        return priority_results

    return [p for p in filtered if p.count("/") <= 5]


def scan_tree_for_skills(tree: Tree, subpath: Optional[str] = None) -> list[ScanResult]:
    """Scan a repository tree and return skill candidates."""
    return [ScanResult(repo_path=path) for path in find_skill_md_paths(tree, subpath)]



def parse_skill_from_content(
    content: str,
    repo_path: str,
    include_internal: bool = False,
) -> Optional[Skill]:
    """
    Parse SKILL.md content and extract skill metadata.

    Args:
        content: Raw SKILL.md content
        repo_path: Path within the repo (e.g., "skills/react/SKILL.md")
        include_internal: Whether to include internal skills

    Returns:
        Skill object if valid, None otherwise
    """
    try:
        post = frontmatter.loads(content)
        metadata = post.metadata

        name = metadata.get("name")
        description = metadata.get("description")

        if not name or not description:
            return None

        if not isinstance(name, str) or not isinstance(description, str):
            return None

        skill_metadata = metadata.get("metadata", {})
        is_internal = skill_metadata.get("internal", False) if isinstance(skill_metadata, dict) else False

        if is_internal and not include_internal:
            return None

        return Skill(
            name=name.strip(),
            description=description.strip(),
            repo_path=repo_path,
            raw_content=content,
            metadata=skill_metadata if isinstance(skill_metadata, dict) else None,
        )
    except Exception:
        return None



def to_skill_slug(name: str) -> str:
    """
    Convert a skill name to a URL-safe slug.
    Must match the server-side toSkillSlug() exactly.
    """
    import re
    slug = name.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug
