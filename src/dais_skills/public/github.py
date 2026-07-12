import httpx
from dataclasses import dataclass
from urllib.parse import urlparse
from dais_skills.exception import SkillException


API_BASE_URL = "https://api.github.com"
RAW_BASE_URL = "https://raw.githubusercontent.com"
USER_AGENT = "dais-skills"


class GitHubError(SkillException):
    """Base error for GitHub API / URL interactions."""


class InvalidGitHubUrlError(GitHubError):
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Unsupported GitHub repository URL: {url}")


class GitHubApiError(GitHubError):
    def __init__(self, api_path: str, status_code: int):
        self.api_path = api_path
        self.status_code = status_code
        super().__init__(
            f"GitHub API request failed: HTTP {status_code} for {api_path}"
        )


class GitHubTreeFetchError(GitHubError):
    def __init__(self, owner_repo: str, tried_refs: list[str], cause: Exception | None = None):
        self.owner_repo = owner_repo
        self.tried_refs = list(tried_refs)
        self.cause = cause
        refs = ", ".join(tried_refs) if tried_refs else "(none)"
        message = f"Unable to fetch repository tree for {owner_repo} (tried refs: {refs})"
        if cause is not None:
            message = f"{message}: {cause}"
        super().__init__(message)


class GitHubBlobFetchError(GitHubError):
    def __init__(self, path: str, status_code: int):
        self.path = path
        self.status_code = status_code
        super().__init__(f"Failed to download file {path}: HTTP {status_code}")


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    repo: str
    ref: str | None = None

    @property
    def owner_repo(self) -> str:
        return f"{self.owner}/{self.repo}"

    @classmethod
    def from_url(cls, repo_url: str) -> "GitHubRepo":
        parsed = urlparse(repo_url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
            raise InvalidGitHubUrlError(repo_url)

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise InvalidGitHubUrlError(repo_url)

        owner = parts[0]
        repo = parts[1].removesuffix(".git")

        ref = None
        if len(parts) >= 4 and parts[2] == "tree":
            ref = "/".join(parts[3:])

        return cls(owner=owner, repo=repo, ref=ref)


@dataclass(frozen=True)
class GitHubBlob:
    path: str
    size: int | None = None


class GitHubClient:
    """Thin async wrapper around GitHub's tree and raw endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def fetch_tree(self, repo: GitHubRepo) -> tuple[str, list[GitHubBlob]]:
        refs_to_try = [repo.ref] if repo.ref else ["main", "master"]
        last_error: GitHubError | None = None

        for tree_ref in refs_to_try:
            try:
                tree = await self._get_json(
                    f"/repos/{repo.owner_repo}/git/trees/{tree_ref}?recursive=1"
                )
            except GitHubError as exc:
                last_error = exc
                continue

            blobs = [
                GitHubBlob(path=entry["path"], size=entry.get("size"))
                for entry in tree.get("tree", [])
                if entry.get("type") == "blob" and isinstance(entry.get("path"), str)
            ]
            return tree_ref, blobs

        raise GitHubTreeFetchError(
            owner_repo=repo.owner_repo,
            tried_refs=[ref for ref in refs_to_try if ref is not None],
            cause=last_error,
        ) from last_error

    async def fetch_blob(self, repo: GitHubRepo, ref: str, path: str) -> bytes:
        url = f"{RAW_BASE_URL}/{repo.owner}/{repo.repo}/{ref}/{path}"
        response = await self._client.get(url, headers={"User-Agent": USER_AGENT})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubBlobFetchError(path, exc.response.status_code) from exc
        return response.content

    async def fetch_text(self, repo: GitHubRepo, ref: str, path: str) -> str:
        content = await self.fetch_blob(repo, ref, path)
        return content.decode("utf-8", errors="replace")

    async def _get_json(self, path: str) -> dict:
        response = await self._client.get(
            f"{API_BASE_URL}{path}",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubApiError(path, exc.response.status_code) from exc
        return response.json()


__all__ = [
    "GitHubError",
    "InvalidGitHubUrlError",
    "GitHubApiError",
    "GitHubTreeFetchError",
    "GitHubBlobFetchError",

    "GitHubRepo",
    "GitHubBlob",
    "GitHubClient",
]
