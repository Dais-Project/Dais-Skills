import httpx

from .exceptions import ScannerError
from .github import GitHubScanner, ScannedSkill


async def scan_repo(repo_url: str) -> list[ScannedSkill]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        scanner = GitHubScanner(client)
        return await scanner.scan_repo(repo_url)


__all__ = ["scan_repo", "ScannedSkill", "ScannerError"]
