import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx


class DownloaderError(Exception):
    pass


def normalize_skill_path(skill_path: str) -> str:
    normalized = skill_path.strip().strip("/")
    if not normalized:
        raise DownloaderError("Skill path must not be empty")
    if PurePosixPath(normalized).name.lower() == "skill.md":
        normalized = str(PurePosixPath(normalized).parent)
    if normalized in {"", "."}:
        raise DownloaderError("Skill path must point to a skill directory")
    return normalized


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    repo: str
    ref: str | None = None

    @property
    def owner_repo(self) -> str:
        return f"{self.owner}/{self.repo}"


@dataclass(frozen=True)
class GitHubBlob:
    path: str
    size: int | None = None


class GitHubDownloader:
    API_BASE_URL = "https://api.github.com"
    RAW_BASE_URL = "https://raw.githubusercontent.com"
    USER_AGENT = "dais-skills"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def download_skill_zip(self, repo_url: str, skill_path: str) -> bytes:
        repo = parse_github_repo_url(repo_url)
        skill_dir = normalize_skill_path(skill_path)
        tree_ref, blobs = await self._fetch_tree(repo)
        skill_blobs = filter_skill_blobs(blobs, skill_dir)
        if not skill_blobs:
            raise DownloaderError(f"Skill path not found: {skill_dir}")

        archive_root = PurePosixPath(skill_dir).name or "skill"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for blob in skill_blobs:
                content = await self._fetch_blob(repo, tree_ref, blob.path)
                relative = PurePosixPath(blob.path).relative_to(PurePosixPath(skill_dir))
                archive_path = str(PurePosixPath(archive_root) / relative)
                zf.writestr(archive_path, content)

        return zip_buffer.getvalue()

    async def _fetch_tree(self, repo: GitHubRepo) -> tuple[str, list[GitHubBlob]]:
        refs_to_try = [repo.ref] if repo.ref else ["main", "master"]
        last_error: DownloaderError | None = None

        for tree_ref in refs_to_try:
            try:
                tree = await self._get_json(
                    f"/repos/{repo.owner_repo}/git/trees/{tree_ref}?recursive=1"
                )
            except DownloaderError as exc:
                last_error = exc
                continue

            blobs = [
                GitHubBlob(path=entry["path"], size=entry.get("size"))
                for entry in tree.get("tree", [])
                if entry.get("type") == "blob" and isinstance(entry.get("path"), str)
            ]
            return tree_ref, blobs

        if last_error is not None:
            raise last_error
        raise DownloaderError(f"Unable to fetch repository tree for {repo.owner_repo}")

    async def _fetch_blob(self, repo: GitHubRepo, ref: str, path: str) -> bytes:
        url = f"{self.RAW_BASE_URL}/{repo.owner}/{repo.repo}/{ref}/{path}"
        response = await self._client.get(url, headers={"User-Agent": self.USER_AGENT})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DownloaderError(
                f"Failed to download file {path}: HTTP {exc.response.status_code}"
            ) from exc
        return response.content

    async def _get_json(self, path: str) -> dict:
        response = await self._client.get(
            f"{self.API_BASE_URL}{path}",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": self.USER_AGENT,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DownloaderError(
                f"GitHub API request failed: HTTP {exc.response.status_code}"
            ) from exc
        return response.json()


def parse_github_repo_url(repo_url: str) -> GitHubRepo:
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
        raise DownloaderError(f"Unsupported GitHub repository URL: {repo_url}")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise DownloaderError(f"Unsupported GitHub repository URL: {repo_url}")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")

    ref = None
    if len(parts) >= 4 and parts[2] == "tree":
        ref = "/".join(parts[3:])

    return GitHubRepo(owner=owner, repo=repo, ref=ref)


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
