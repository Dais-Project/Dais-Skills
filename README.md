# dais-skills

A Python package for programmatically discovering, downloading, and parsing [Agent Skills](https://agentskills.io/home.md).

Currently supports GitHub as a skill source. GitLab, arbitrary Git repositories, and custom sources (e.g. S3) are planned.

> This project is in early development. The API may change at any time and backward compatibility is not guaranteed yet.

[中文文档](./README_zh.md)

## Features

- **Scan a repository**: given a GitHub repo URL, list every skill in it along with its path, name, and description
- **Download a skill**: given a repo URL and a skill path, package that skill directory as a zip byte stream
- **Parse a skill archive**: extract `SKILL.md` metadata (with frontmatter) and every resource file (auto-classified as text or binary) from a zip

## Installation

Requires Python 3.14+.

```bash
uv add dais-skills
# or
pip install dais-skills
```

## Quick Start

### Scan a repository for skills

```python
import asyncio
from dais_skills import scan_repo

async def main():
    skills = await scan_repo("https://github.com/<owner>/<repo>")
    for s in skills:
        print(s.path, "-", s.name)
        print(" ", s.description)

asyncio.run(main())
```

`scan_repo` returns `list[ScannedSkill]`, where each item has:

- `path`: the skill directory path inside the repo
- `name`: the `name` field from the `SKILL.md` frontmatter
- `description`: the `description` field from the `SKILL.md` frontmatter

The scanner walks the priority directories defined by the [Agent Skills specification](https://agentskills.io/home.md) (such as `skills/`, `.claude/skills/`, `.github/skills/`, and so on) and skips irrelevant directories like `node_modules`, `.git`, `dist`, `build`, and `__pycache__`.

### Download a single skill as a zip

```python
import asyncio
from dais_skills import download_skill_zip

async def main():
    data: bytes = await download_skill_zip(
        "https://github.com/<owner>/<repo>",
        "skills/my-skill",
    )
    with open("my-skill.zip", "wb") as f:
        f.write(data)

asyncio.run(main())
```

`skill_path` may point at either the skill directory or the `SKILL.md` inside it. Both forms are treated as equivalent.

You can also pass an existing `httpx.AsyncClient` via the optional keyword-only argument `client` to reuse connections across calls.

### Parse a downloaded skill archive

```python
import zipfile
from dais_skills import Skill

with zipfile.ZipFile("my-skill.zip") as zf:
    skill = Skill.from_zip(zf)

print(skill.name, skill.description)
print("license:", skill.license)
print("compatibility:", skill.compatibility)
print("allowed-tools:", skill.allowed_tools)
print("metadata:", skill.metadata)
print("body:", skill.content[:80])

for res in skill.resources:
    if res.type == "text":
        print("[text]", res.relative, len(res.content))
    else:
        print("[bin] ", res.relative, len(res.content))
```

`Skill.from_zip` will:

1. Locate the skill root inside the zip (the first-level directory containing `SKILL.md`, or the archive root)
2. Parse the frontmatter and body of `SKILL.md`
3. Collect every remaining file as a `SkillResource`, splitting them into `TextResource` and `BinaryResource` via `binaryornot`

## Public API

Exported from the top-level package:

| Name | Description |
| --- | --- |
| `scan_repo(repo_url) -> list[ScannedSkill]` | Scan a repository and return a summary of every skill found |
| `download_skill_zip(repo_url, skill_path, *, client=None) -> bytes` | Download the given skill directory and pack it into a zip; optional `httpx.AsyncClient` reuse |
| `Skill.from_zip(zip_file) -> Skill` | Parse a full skill object from a zip file |
| `ScannedSkill` | Scan-result dataclass (`path`, `name`, `description`) |
| `Skill` | Fully parsed skill dataclass (`name`, `description`, `content`, optional `license` / `compatibility` / `allowed_tools`, `metadata`, `resources`) |
| `SkillResource` | `TextResource \| BinaryResource` |
| `SkillException` | Base exception for this package |
| `ScannerError` | Base error for scanning failures |
| `InvalidRepoUrlError` | Invalid repository URL (scanner) |
| `RepositoryTreeFetchError` | Failed to fetch repository tree |
| `DownloaderError` | Base error for download failures |
| `InvalidSkillPathError` | Invalid skill path |
| `SkillPathNotFoundError` | Skill path not found in repository |
| `SkillTreeFetchError` | Failed to fetch repository tree for download |
| `SkillFileDownloadError` | Failed to download a skill file |
| `ExtractorException` | Base error for archive extraction failures |
| `InvalidSkillArchiveError` | Invalid skill archive |
| `SkillRootNotFoundError` | Skill root not found in archive |
| `SkillMdNotFoundError` | `SKILL.md` not found in archive |

GitHub client exceptions (`GitHubError`, `InvalidGitHubUrlError`, `GitHubApiError`, `GitHubTreeFetchError`, `GitHubBlobFetchError`) are available from `dais_skills.public`.

## Development

```bash
uv sync
uv run pytest              # run unit tests
uv run pytest -m smoke     # run end-to-end smoke tests that hit real network services
```

## Roadmap

- [x] Scan skills in a GitHub repository
- [x] Download and package a single skill from GitHub
- [x] Parse a skill archive
- [ ] GitLab repository support
- [ ] Arbitrary remote Git repository support
- [ ] S3 and other custom sources
