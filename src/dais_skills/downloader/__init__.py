import httpx
from .github import GitHubDownloader


class DownloaderError(Exception):
    pass

async def download_skill_zip(repo_url: str, skill_path: str) -> bytes:
    async with httpx.AsyncClient(timeout=10.0) as client:
        downloader = GitHubDownloader(client)
        return await downloader.download_skill_zip(repo_url, skill_path)

__all__ = ["download_skill_zip"]
