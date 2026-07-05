import httpx
import pytest

from dais_skills.public.github import GitHubBlob
from dais_skills.scanner import scan_repo
from dais_skills.scanner.github import (
    GitHubScanner,
    ScannedSkill,
    ScannerError,
    find_skill_md_paths,
    parse_skill_from_content,
)


class TestFindSkillMdPaths:
    def test_returns_empty_when_no_skill_md(self):
        blobs = [GitHubBlob("readme.md"), GitHubBlob("src/main.py")]

        assert find_skill_md_paths(blobs) == []

    def test_ignores_root_skill_md(self):
        blobs = [GitHubBlob("SKILL.md"), GitHubBlob("skills/foo/SKILL.md")]

        assert find_skill_md_paths(blobs) == ["skills/foo/SKILL.md"]

    def test_finds_skills_in_priority_containers(self):
        blobs = [
            GitHubBlob("skills/foo/SKILL.md"),
            GitHubBlob(".claude/skills/bar/SKILL.md"),
            GitHubBlob("random/deeply/nested/SKILL.md"),
        ]

        result = find_skill_md_paths(blobs)

        assert "skills/foo/SKILL.md" in result
        assert ".claude/skills/bar/SKILL.md" in result
        assert "random/deeply/nested/SKILL.md" not in result

    def test_skips_common_ignored_directories(self):
        blobs = [
            GitHubBlob("skills/node_modules/pkg/SKILL.md"),
            GitHubBlob("skills/valid/SKILL.md"),
        ]

        result = find_skill_md_paths(blobs)

        assert result == ["skills/valid/SKILL.md"]

    def test_prefers_parent_over_nested_when_both_present(self):
        blobs = [
            GitHubBlob("skills/foo/SKILL.md"),
            GitHubBlob("skills/foo/sub/SKILL.md"),
        ]

        result = find_skill_md_paths(blobs)

        assert result == ["skills/foo/SKILL.md"]

    def test_deduplicates_across_priority_prefixes(self):
        blobs = [GitHubBlob("skills/foo/SKILL.md")]

        result = find_skill_md_paths(blobs)

        assert result == ["skills/foo/SKILL.md"]

    def test_ignores_files_that_only_end_with_skill_md(self):
        blobs = [
            GitHubBlob("docs/myskill.md"),
            GitHubBlob("WhatEverSkill.md"),
            GitHubBlob("skills/foo/SKILL.md"),
        ]

        result = find_skill_md_paths(blobs)

        assert result == ["skills/foo/SKILL.md"]


class TestParseSkillFromContent:
    def test_parses_name_description_and_dir(self):
        content = "---\nname: Foo\ndescription: A foo skill\n---\nbody"

        skill = parse_skill_from_content(content, "skills/foo/SKILL.md")

        assert skill == ScannedSkill(path="skills/foo", name="Foo", description="A foo skill")

    def test_returns_none_when_metadata_missing(self):
        content = "---\nname: Foo\n---\nbody"

        assert parse_skill_from_content(content, "skills/foo/SKILL.md") is None

    def test_returns_none_when_metadata_not_string(self):
        content = "---\nname: 123\ndescription: valid\n---\nbody"

        assert parse_skill_from_content(content, "skills/foo/SKILL.md") is None

    def test_strips_whitespace(self):
        content = "---\nname: '  Foo  '\ndescription: '  Bar  '\n---\n"

        skill = parse_skill_from_content(content, "skills/foo/SKILL.md")

        assert skill is not None
        assert skill.name == "Foo"
        assert skill.description == "Bar"


class TestGitHubScanner:
    @pytest.mark.asyncio
    async def test_scan_repo_returns_discovered_skills(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(
                    200,
                    json={
                        "tree": [
                            {"path": "skills/foo/SKILL.md", "type": "blob"},
                            {"path": "skills/foo/asset.txt", "type": "blob"},
                            {"path": "skills/bar/SKILL.md", "type": "blob"},
                            {"path": "random/nested/deep/SKILL.md", "type": "blob"},
                        ]
                    },
                )
            if request.url.path == "/octo/demo/main/skills/foo/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Foo\ndescription: Foo skill\n---\nbody",
                )
            if request.url.path == "/octo/demo/main/skills/bar/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Bar\ndescription: Bar skill\n---\nbody",
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            scanner = GitHubScanner(client)
            skills = await scanner.scan_repo("https://github.com/octo/demo/tree/main")

        assert skills == [
            ScannedSkill(path="skills/foo", name="Foo", description="Foo skill"),
            ScannedSkill(path="skills/bar", name="Bar", description="Bar skill"),
        ]

    @pytest.mark.asyncio
    async def test_scan_repo_falls_back_to_master(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(404)
            if request.url.path == "/repos/octo/demo/git/trees/master":
                return httpx.Response(
                    200,
                    json={"tree": [{"path": "skills/foo/SKILL.md", "type": "blob"}]},
                )
            if request.url.path == "/octo/demo/master/skills/foo/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Foo\ndescription: Foo skill\n---\nbody",
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            scanner = GitHubScanner(client)
            skills = await scanner.scan_repo("https://github.com/octo/demo")

        assert skills == [ScannedSkill(path="skills/foo", name="Foo", description="Foo skill")]

    @pytest.mark.asyncio
    async def test_scan_repo_raises_when_tree_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            scanner = GitHubScanner(client)
            with pytest.raises(ScannerError):
                await scanner.scan_repo("https://github.com/octo/demo")

    @pytest.mark.asyncio
    async def test_scan_repo_skips_invalid_skill_md(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(
                    200,
                    json={
                        "tree": [
                            {"path": "skills/good/SKILL.md", "type": "blob"},
                            {"path": "skills/bad/SKILL.md", "type": "blob"},
                        ]
                    },
                )
            if request.url.path == "/octo/demo/main/skills/good/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Good\ndescription: valid\n---\n",
                )
            if request.url.path == "/octo/demo/main/skills/bad/SKILL.md":
                return httpx.Response(200, text="no frontmatter here")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            scanner = GitHubScanner(client)
            skills = await scanner.scan_repo("https://github.com/octo/demo")

        assert skills == [ScannedSkill(path="skills/good", name="Good", description="valid")]


class TestTopLevelScanRepo:
    @pytest.mark.asyncio
    async def test_function_uses_external_client_context(self, monkeypatch: pytest.MonkeyPatch):
        sentinel_client = object()

        class FakeAsyncClient:
            async def __aenter__(self):
                return sentinel_client

            async def __aexit__(self, exc_type, exc, tb):
                return None

        def fake_client_factory(*args, **kwargs):
            return FakeAsyncClient()

        class FakeScanner:
            def __init__(self, client):
                assert client is sentinel_client

            async def scan_repo(self, repo_url: str) -> list[ScannedSkill]:
                assert repo_url == "https://github.com/octo/demo"
                return [ScannedSkill(path="skills/foo", name="Foo", description="d")]

        monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)
        monkeypatch.setattr("dais_skills.scanner.GitHubScanner", FakeScanner)

        result = await scan_repo("https://github.com/octo/demo")

        assert result == [ScannedSkill(path="skills/foo", name="Foo", description="d")]
