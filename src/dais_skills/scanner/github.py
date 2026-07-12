from dataclasses import dataclass
from pathlib import PurePosixPath

import frontmatter
import httpx

from dais_skills.public.github import (
    GitHubBlob,
    GitHubClient,
    GitHubError,
    GitHubRepo,
)

from .exceptions import InvalidRepoUrlError, RepositoryTreeFetchError, ScannerError


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


@dataclass(frozen=True)
class ScannedSkill:
    path: str
    name: str
    description: str


class GitHubScanner:
    def __init__(self, client: httpx.AsyncClient):
        self._github = GitHubClient(client)

    async def scan_repo(self, repo_url: str) -> list[ScannedSkill]:
        try:
            repo = GitHubRepo.from_url(repo_url)
        except GitHubError as exc:
            raise InvalidRepoUrlError(repo_url, str(exc)) from exc

        try:
            tree_ref, blobs = await self._github.fetch_tree(repo)
        except GitHubError as exc:
            raise RepositoryTreeFetchError(str(exc)) from exc

        skill_md_paths = find_skill_md_paths(blobs)

        skills: list[ScannedSkill] = []
        for skill_md_path in skill_md_paths:
            try:
                content = await self._github.fetch_text(repo, tree_ref, skill_md_path)
            except GitHubError:
                continue
            skill = parse_skill_from_content(content, skill_md_path)
            if skill is not None:
                skills.append(skill)

        return skills


def _is_skill_md(path: str) -> bool:
    return "/" in path and path.rsplit("/", 1)[-1].lower() == "skill.md"


def find_skill_md_paths(blobs: list[GitHubBlob]) -> list[str]:
    filtered = [blob.path for blob in blobs if _is_skill_md(blob.path)]
    if not filtered:
        return []

    priority_results: list[str] = []
    seen: set[str] = set()
    lower_skill_md_set = {path.lower() for path in filtered}

    for priority_prefix in PRIORITY_PREFIXES:
        is_container = priority_prefix != ""

        for skill_md in filtered:
            if not skill_md.startswith(priority_prefix):
                continue

            rest = skill_md[len(priority_prefix):]
            parts = rest.split("/")

            if len(parts) == 2:
                if skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)
                continue

            if (
                is_container
                and len(parts) == 3
                and parts[0] not in SKIP_DIRS
                and parts[1] not in SKIP_DIRS
            ):
                parent_skill_md = f"{priority_prefix}{parts[0]}/SKILL.md".lower()
                if parent_skill_md not in lower_skill_md_set and skill_md not in seen:
                    priority_results.append(skill_md)
                    seen.add(skill_md)

    if priority_results:
        return priority_results

    return [
        path
        for path in filtered
        if path.count("/") <= 5
        and not any(part in SKIP_DIRS for part in path.split("/"))
    ]


def parse_skill_from_content(content: str, repo_path: str) -> ScannedSkill | None:
    try:
        post = frontmatter.loads(content)
    except Exception:
        return None

    name = post.metadata.get("name")
    description = post.metadata.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        return None

    return ScannedSkill(
        path=str(PurePosixPath(repo_path).parent),
        name=name.strip(),
        description=description.strip(),
    )


__all__ = [
    "ScannerError",
    "InvalidRepoUrlError",
    "RepositoryTreeFetchError",
    "ScannedSkill",
    "GitHubScanner",
    "find_skill_md_paths",
    "parse_skill_from_content",
]
