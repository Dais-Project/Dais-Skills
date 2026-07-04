"""GitHub Trees API client with rate limit handling."""

import httpx
from typing import Optional, Callable
from ...models import RepoTree, TreeEntry


async def _fetch_tree_branch(
    owner_repo: str,
    branch: str,
    token: Optional[str] = None,
) -> tuple[Optional[RepoTree], bool]:
    """
    Fetch a single branch tree from GitHub Trees API.
    
    Returns:
        Tuple of (RepoTree or None, rate_limited: bool)
    """
    url = f"https://api.github.com/repos/{owner_repo}/git/trees/{branch}?recursive=1"
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
                        type=entry["type"],
                        sha=entry["sha"],
                        size=entry.get("size"),
                    )
                    for entry in data.get("tree", [])
                ]
                return (
                    RepoTree(
                        sha=data["sha"],
                        branch=branch,
                        tree=tree_entries,
                    ),
                    False,
                )
            
            # GitHub signals rate-limit with 403 + X-RateLimit-Remaining: 0
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
) -> Optional[RepoTree]:
    """
    Fetch the full recursive tree for a GitHub repo.
    
    Tries branches in order: ref (if specified), then HEAD, then main, then master.
    
    Authentication is lazy: by default the call goes out unauthenticated,
    which is enough for the vast majority of users (60 req/hr per IP).
    Only if GitHub responds with a rate-limit 403 do we ask the optional
    `get_token` callback for a token and retry.
    
    Args:
        owner_repo: Repository in "owner/repo" format
        ref: Optional branch/tag/commit to fetch
        get_token: Optional callback to get GitHub token when rate limited
        
    Returns:
        RepoTree if successful, None otherwise
    """
    branches = [ref] if ref else ["HEAD", "main", "master"]
    
    # First pass: unauthenticated
    rate_limited = False
    for branch in branches:
        tree, is_rate_limited = await _fetch_tree_branch(owner_repo, branch, None)
        if tree:
            return tree
        if is_rate_limited:
            # All branches share the same rate-limit bucket on this IP
            rate_limited = True
            break
    
    if not rate_limited or not get_token:
        return None
    
    # Lazy fallback: rate limit hit and a token resolver was provided
    token = get_token()
    if not token:
        return None
    
    for branch in branches:
        tree, _ = await _fetch_tree_branch(owner_repo, branch, token)
        if tree:
            return tree
    
    return None
