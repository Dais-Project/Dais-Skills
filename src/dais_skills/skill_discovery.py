"""Skill discovery from GitHub repository trees."""

import httpx
import frontmatter
from typing import Optional
from .models import RepoTree, Skill


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


def find_skill_md_paths(tree: RepoTree, subpath: Optional[str] = None) -> list[str]:
    """
    Find all SKILL.md file paths in a repo tree.
    Applies the same priority directory logic as the TypeScript implementation.
    
    Args:
        tree: Repository tree from GitHub API
        subpath: Optional subpath to filter results
        
    Returns:
        List of SKILL.md file paths
    """
    # Find all blob entries that are SKILL.md files (case-insensitive)
    all_skill_mds = [
        entry.path
        for entry in tree.tree
        if entry.type == "blob" and entry.path.lower().endswith("skill.md")
    ]
    
    # Apply subpath filter
    prefix = (subpath + "/") if subpath and not subpath.endswith("/") else (subpath or "")
    filtered = [
        p for p in all_skill_mds
        if p.startswith(prefix) or p == prefix + "SKILL.md"
    ] if prefix else all_skill_mds
    
    if not filtered:
        return []
    
    # Check priority directories first
    priority_results = []
    seen = set()
    lower_skill_md_set = {p.lower() for p in filtered}
    
    for priority_prefix in PRIORITY_PREFIXES:
        full_prefix = prefix + priority_prefix
        is_container = priority_prefix != ""
        
        for skill_md in filtered:
            # Check if this SKILL.md is inside the priority dir
            if not skill_md.startswith(full_prefix):
                continue
            
            rest = skill_md[len(full_prefix):]
            
            # Direct SKILL.md in the priority dir (e.g., "skills/SKILL.md")
            if rest.lower() == "skill.md":
                if skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)
                continue
            
            # SKILL.md one level deep (e.g., "skills/react-best-practices/SKILL.md")
            parts = rest.split("/")
            if len(parts) == 2 and parts[1].lower() == "skill.md":
                if skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)
                continue
            
            # SKILL.md two levels deep under a known container prefix
            # (e.g., "skills/<category>/<skill>/SKILL.md")
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
    
    # If we found skills in priority dirs, return those
    if priority_results:
        return priority_results
    
    # Fallback: return all SKILL.md files found (limited to 5 levels deep)
    return [p for p in filtered if p.count("/") <= 5]


async def fetch_skill_md_content(
    owner_repo: str,
    branch: str,
    skill_md_path: str,
) -> Optional[str]:
    """
    Fetch a single SKILL.md from raw.githubusercontent.com.
    
    Args:
        owner_repo: Repository in "owner/repo" format
        branch: Branch name
        skill_md_path: Path to SKILL.md within the repo
        
    Returns:
        Raw content string, or None on failure
    """
    url = f"https://raw.githubusercontent.com/{owner_repo}/{branch}/{skill_md_path}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
            return None
    except Exception:
        return None


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
        
        # Required fields
        name = metadata.get("name")
        description = metadata.get("description")
        
        if not name or not description:
            return None
        
        if not isinstance(name, str) or not isinstance(description, str):
            return None
        
        # Skip internal skills unless explicitly requested
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
