import httpx
from .exceptions import (
    DownloaderError,
    InvalidSkillPathError,
    SkillFileDownloadError,
    SkillPathNotFoundError,
    SkillTreeFetchError,
)
from .github import GitHubDownloader


async def download_skill_zip(repo_url: str, skill_path: str, *, client: httpx.AsyncClient | None = None) -> bytes:
    if client is not None:
        return await GitHubDownloader(client).download_skill_zip(repo_url, skill_path)
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await GitHubDownloader(client).download_skill_zip(repo_url, skill_path)

__all__ = [
    "download_skill_zip",

    "DownloaderError",
    "InvalidSkillPathError",
    "SkillPathNotFoundError",
    "SkillTreeFetchError",
    "SkillFileDownloadError",
]
