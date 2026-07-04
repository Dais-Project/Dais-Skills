# dais-skills

A Python package for scanning and downloading agent skills from specified GitHub repositories.

## Features

- **GitHub Repository Scanning**: Scan any GitHub repo for agent skills
- **Multiple Input Formats**: Support various source formats (shorthand, URL, with branch/subpath)
- **Priority Directory Discovery**: Automatically searches known skill container directories
- **Rate Limit Handling**: Starts with anonymous access, falls back to token auth when rate limited
- **Async/Concurrent**: Parallel fetching of skill metadata for fast discovery
- **Skill Filtering**: Filter by skill name using `@skill-name` syntax

## Installation

```bash
pip install dais-skills
```

## Usage

### Basic Scanning

```python
import asyncio
from dais_skills import scan_repo

async def main():
    # Scan a repository
    skills = await scan_repo("vercel-labs/agent-skills")
    
    for skill in skills:
        print(f"{skill.name}: {skill.description}")
        print(f"  Path: {skill.repo_path}")

asyncio.run(main())
```

### Supported Source Formats

```python
# Owner/repo shorthand
skills = await scan_repo("vercel-labs/agent-skills")

# With specific branch
skills = await scan_repo("owner/repo", ref="develop")

# With subpath
skills = await scan_repo("owner/repo/skills/curated")

# Full GitHub URL
skills = await scan_repo("https://github.com/owner/repo/tree/main/skills")

# Filter to specific skill using @ syntax
skills = await scan_repo("vercel-labs/agent-skills@deploy-to-vercel")
```

### With GitHub Token (for rate limits)

```python
import os

def get_github_token():
    return os.getenv("GITHUB_TOKEN")

skills = await scan_repo(
    "vercel-labs/agent-skills",
    get_token=get_github_token
)
```

### Including Internal Skills

By default, skills marked as `internal: true` in their metadata are skipped. To include them:

```python
skills = await scan_repo("owner/repo", include_internal=True)
```

## How It Works

This implementation is based on the TypeScript `skills` CLI and follows the same scanning strategy:

1. **Parse Source**: Supports `owner/repo`, URLs, subpaths, and skill filters
2. **Fetch Repo Tree**: Uses GitHub Trees API (recursive) to get all files
3. **Discover Skills**: Searches priority directories for `SKILL.md` files:
   - `skills/`, `skills/.curated/`, `skills/.experimental/`
   - `.agents/skills/`, `.claude/skills/`, `.kiro/skills/`, etc.
4. **Fetch Content**: Retrieves each `SKILL.md` from raw.githubusercontent.com
5. **Parse Frontmatter**: Extracts `name`, `description`, and `metadata` from YAML frontmatter
6. **Filter**: Applies skill name filters if specified

## Data Model

### Skill

```python
@dataclass
class Skill:
    name: str                    # Skill name from frontmatter
    description: str             # Skill description
    repo_path: str               # Path within repo (e.g., "skills/react/SKILL.md")
    raw_content: str             # Full SKILL.md content
    metadata: Optional[dict]     # Additional metadata from frontmatter
```

## Requirements

- Python >= 3.14
- httpx >= 0.28.1
- python-frontmatter >= 1.1.0

## License

See LICENSE file for details.
