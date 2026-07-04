"""GitHub Trees API client with rate limit handling."""

import httpx
from typing import Optional, Callable
from ...models import Tree, TreeEntry


async def _fetch_tree_branch(
    owner_repo: str,
    tree_ref: str,
    token: Optional[str] = None,
) -> tuple[Optional[list[TreeEntry]], bool]:
    """
    Fetch a single branch tree from GitHub Trees API.

    Returns:
        Tuple of (tree entries or None, rate_limited: bool)
    """
    url = f"https://api.github.com/repos/{owner_repo}/git/trees/{tree_ref}?recursive=1"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "dais-skills",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                tree_entries = [
                    TreeEntry(
                        path=entry["path"],
                        kind="directory" if entry["type"] == "tree" else "file",
                        size=entry.get("size"),
                    )
                    for entry in data.get("tree", [])
                ]
                return tree_entries, False

            rate_limited = (
                response.status_code == 403
                and response.headers.get("x-ratelimit-remaining") == "0"
            )
            return None, rate_limited

    except Exception:
        return None, False


async def fetch_repo_tree(
    owner_repo: str,
    ref: Optional[str] = None,
    get_token: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[Tree]:
    """
    Fetch the full recursive tree for a GitHub repo.

    Tries refs in order: explicit ref (if specified), then main, then master.
    """
    refs_to_try = [ref] if ref else ["main", "master"]

    rate_limited = False
    for tree_ref in refs_to_try:
        entries, is_rate_limited = await _fetch_tree_branch(owner_repo, tree_ref, None)
        if entries is not None:
            return Tree(ref=tree_ref, entries=entries)
        if is_rate_limited:
            rate_limited = True
            break

    if not rate_limited or not get_token:
        return None

    token = get_token()
    if not token:
        return None

    for tree_ref in refs_to_try:
        entries, _ = await _fetch_tree_branch(owner_repo, tree_ref, token)
        if entries is not None:
            return Tree(ref=tree_ref, entries=entries)

    return None
