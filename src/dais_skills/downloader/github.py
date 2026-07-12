import io
import zipfile
import httpx
from pathlib import PurePosixPath
from dais_skills.public.github import (
    GitHubBlob,
    GitHubClient,
    GitHubError,
    GitHubRepo,
)
from .exceptions import (
    DownloaderError,
    InvalidRepoUrlError,
    InvalidSkillPathError,
    SkillFileDownloadError,
    SkillPathNotFoundError,
    SkillTreeFetchError,
)


def normalize_skill_path(skill_path: str) -> str:
    normalized = skill_path.strip().strip("/")
    if len(normalized) == 0:
        raise InvalidSkillPathError(skill_path, "Skill path must not be empty")
    if PurePosixPath(normalized).name.lower() == "skill.md":
        normalized = str(PurePosixPath(normalized).parent)
    if normalized in {"", "."}:
        raise InvalidSkillPathError(skill_path, "Skill path must point to a skill directory")
    return normalized

class GitHubDownloader:
    def __init__(self, client: httpx.AsyncClient):
        self._github = GitHubClient(client)

    async def download_skill_zip(self, repo_url: str, skill_path: str) -> bytes:
        try:
            repo = GitHubRepo.from_url(repo_url)
        except GitHubError as exc:
            raise InvalidRepoUrlError(repo_url, str(exc)) from exc

        skill_dir = normalize_skill_path(skill_path)
        try:
            tree_ref, blobs = await self._github.fetch_tree(repo)
        except GitHubError as exc:
            raise SkillTreeFetchError(str(exc)) from exc

        skill_blobs = filter_skill_blobs(blobs, skill_dir)
        if not skill_blobs:
            raise SkillPathNotFoundError(skill_dir)

        archive_root = PurePosixPath(skill_dir).name or "skill"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for blob in skill_blobs:
                try:
                    content = await self._github.fetch_blob(repo, tree_ref, blob.path)
                except GitHubError as exc:
                    raise SkillFileDownloadError(blob.path, str(exc)) from exc
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
    "InvalidRepoUrlError",
    "InvalidSkillPathError",
    "SkillPathNotFoundError",
    "SkillTreeFetchError",
    "SkillFileDownloadError",

    "filter_skill_blobs",
    "normalize_skill_path",
]
