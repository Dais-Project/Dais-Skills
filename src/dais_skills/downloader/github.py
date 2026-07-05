import io
import zipfile
from pathlib import PurePosixPath

import httpx

from dais_skills.public.github import (
    GitHubBlob,
    GitHubClient,
    GitHubError,
    GitHubRepo,
    parse_github_repo_url,
)

from .exceptions import DownloaderError


def normalize_skill_path(skill_path: str) -> str:
    normalized = skill_path.strip().strip("/")
    if not normalized:
        raise DownloaderError("Skill path must not be empty")
    if PurePosixPath(normalized).name.lower() == "skill.md":
        normalized = str(PurePosixPath(normalized).parent)
    if normalized in {"", "."}:
        raise DownloaderError("Skill path must point to a skill directory")
    return normalized


class GitHubDownloader:
    def __init__(self, client: httpx.AsyncClient):
        self._github = GitHubClient(client)

    async def download_skill_zip(self, repo_url: str, skill_path: str) -> bytes:
        repo = parse_github_repo_url(repo_url)
        skill_dir = normalize_skill_path(skill_path)
        try:
            tree_ref, blobs = await self._github.fetch_tree(repo)
        except GitHubError as exc:
            raise DownloaderError(str(exc)) from exc

        skill_blobs = filter_skill_blobs(blobs, skill_dir)
        if not skill_blobs:
            raise DownloaderError(f"Skill path not found: {skill_dir}")

        archive_root = PurePosixPath(skill_dir).name or "skill"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for blob in skill_blobs:
                try:
                    content = await self._github.fetch_blob(repo, tree_ref, blob.path)
                except GitHubError as exc:
                    raise DownloaderError(str(exc)) from exc
                relative = PurePosixPath(blob.path).relative_to(PurePosixPath(skill_dir))
                archive_path = str(PurePosixPath(archive_root) / relative)
                zf.writestr(archive_path, content)

        return zip_buffer.getvalue()


def filter_skill_blobs(blobs: list[GitHubBlob], skill_dir: str) -> list[GitHubBlob]:
    prefix = f"{skill_dir}/"
    filtered = [
        blob
        for blob in blobs
        if blob.path == f"{skill_dir}/SKILL.md"
        or blob.path == f"{skill_dir}/skill.md"
        or blob.path.startswith(prefix)
    ]
    return sorted(filtered, key=lambda blob: blob.path)


__all__ = [
    "DownloaderError",
    "GitHubBlob",
    "GitHubDownloader",
    "GitHubRepo",
    "filter_skill_blobs",
    "normalize_skill_path",
    "parse_github_repo_url",
]
