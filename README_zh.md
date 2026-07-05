# dais-skills

一个用于程序化发现、下载和解析 [Agent Skills](https://agentskills.io/home.md) 的 Python 包。

当前仅支持 GitHub 作为 skill 源，后续计划扩展至 GitLab、任意 Git 仓库和 S3 等自定义源。

> 本项目处于早期开发阶段，API 可能随时变动，暂不保证向后兼容。

[English README](./README.md)

## 特性

- **扫描仓库**：给定一个 GitHub 仓库 URL，解析出仓库内所有 skill 的路径、名称与 description
- **下载 skill**：给定仓库 URL 与 skill 路径，将该 skill 目录打包为 zip 字节流返回
- **解析压缩包**：从 zip 中提取 `SKILL.md` 元数据（含 frontmatter）与全部资源文件（自动区分文本与二进制）

## 安装

需要 Python 3.14+。

```bash
uv add dais-skills
# 或
pip install dais-skills
```

## 快速上手

### 扫描仓库中的所有 skill

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

`scan_repo` 返回 `list[ScannedSkill]`，每个元素包含：

- `path`：skill 目录在仓库中的路径
- `name`：来自 `SKILL.md` frontmatter 的 `name` 字段
- `description`：来自 `SKILL.md` frontmatter 的 `description` 字段

扫描器按 [Agent Skills 规范](https://agentskills.io/home.md) 中的优先目录顺序（如 `skills/`、`.claude/skills/`、`.github/skills/` 等）查找 `SKILL.md`，并自动跳过 `node_modules`、`.git`、`dist`、`build`、`__pycache__` 等无关目录。

### 下载单个 skill 为 zip

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

`skill_path` 可以指向 skill 目录，也可以直接指向该目录下的 `SKILL.md`——两者等价。

### 解析下载后的 skill 压缩包

```python
import zipfile
from dais_skills import Skill

with zipfile.ZipFile("my-skill.zip") as zf:
    skill = Skill.from_zip(zf)

print(skill.name, skill.description)
print("license:", skill.license)
print("compatibility:", skill.compatibility)
print("allowed-tools:", skill.allowed_tools)

for res in skill.resources:
    if res.type == "text":
        print("[text]", res.relative, len(res.content))
    else:
        print("[bin] ", res.relative, len(res.content))
```

`Skill` 会：

1. 定位 zip 中的 skill 根目录（第一层包含 `SKILL.md` 的目录，或存档根）
2. 解析 `SKILL.md` 的 frontmatter 与正文
3. 将其余文件收集为 `SkillResource`，通过 `binaryornot` 自动分为 `TextResource` 与 `BinaryResource`

## 公共 API

从顶层包导出：

| 名称 | 说明 |
| --- | --- |
| `scan_repo(repo_url) -> list[ScannedSkill]` | 扫描仓库并返回其中所有 skill 摘要 |
| `download_skill_zip(repo_url, skill_path) -> bytes` | 下载指定 skill 目录并打包为 zip |
| `Skill.from_zip(zip_file) -> Skill` | 从 zip 文件解析完整的 skill 对象 |
| `ScannedSkill` | 扫描结果 dataclass |
| `Skill` | 解析后的完整 skill dataclass |
| `SkillResource` | `TextResource \| BinaryResource` |
| `SkillException` | 包内异常基类 |

各子模块自身的异常类型（`ScannerError`、`DownloaderError`、`InvalidSkillArchiveError`、`GitHubError`）可从对应子模块导入。

## 开发

```bash
uv sync
uv run pytest              # 运行单元测试
uv run pytest -m smoke     # 运行访问真实网络的端到端冒烟测试
```

## Roadmap

- [x] GitHub 仓库 skill 扫描
- [x] GitHub 单 skill 下载与打包
- [x] skill 压缩包解析
- [ ] GitLab 仓库支持
- [ ] 任意远程 Git 仓库支持
