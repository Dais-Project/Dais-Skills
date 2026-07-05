import io
import zipfile

import httpx
import pytest

from dais_skills.downloader import download_skill_zip
from dais_skills.downloader.github import (
    DownloaderError,
    GitHubDownloader,
    filter_skill_blobs,
    normalize_skill_path,
)
from dais_skills.extractor import Skill
from dais_skills.public.github import GitHubBlob


class TestNormalizeSkillPath:
    def test_accept_directory(self):
        assert normalize_skill_path("skills/demo") == "skills/demo"

    def test_convert_skill_md_path_to_directory(self):
        assert normalize_skill_path("skills/demo/SKILL.md") == "skills/demo"

    def test_reject_empty_path(self):
        with pytest.raises(DownloaderError, match="must not be empty"):
            normalize_skill_path("  ")


class TestFilterSkillBlobs:
    def test_filter_only_target_directory(self):
        blobs = [
            GitHubBlob("skills/demo/SKILL.md"),
            GitHubBlob("skills/demo/readme.txt"),
            GitHubBlob("skills/demo/assets/logo.bin"),
            GitHubBlob("skills/other/SKILL.md"),
        ]

        filtered = filter_skill_blobs(blobs, "skills/demo")

        assert [blob.path for blob in filtered] == [
            "skills/demo/SKILL.md",
            "skills/demo/assets/logo.bin",
            "skills/demo/readme.txt",
        ]


class TestGitHubDownloader:
    @pytest.mark.asyncio
    async def test_download_skill_zip_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(
                    200,
                    json={
                        "tree": [
                            {"path": "skills/demo/SKILL.md", "type": "blob"},
                            {"path": "skills/demo/readme.txt", "type": "blob"},
                            {"path": "skills/demo/assets/logo.bin", "type": "blob"},
                            {"path": "skills/other/SKILL.md", "type": "blob"},
                        ]
                    },
                )
            if request.url.path == "/octo/demo/main/skills/demo/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Demo\ndescription: Downloaded skill\n---\nBody",
                )
            if request.url.path == "/octo/demo/main/skills/demo/readme.txt":
                return httpx.Response(200, text="hello")
            if request.url.path == "/octo/demo/main/skills/demo/assets/logo.bin":
                return httpx.Response(200, content=b"\x00\x01")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            downloader = GitHubDownloader(client)
            zip_bytes = await downloader.download_skill_zip(
                "https://github.com/octo/demo/tree/main",
                "skills/demo",
            )

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert sorted(zf.namelist()) == [
                "demo/SKILL.md",
                "demo/assets/logo.bin",
                "demo/readme.txt",
            ]
            skill = Skill.from_zip(zf)

        assert skill.name == "Demo"
        assert skill.description == "Downloaded skill"
        resources = {resource.relative: resource for resource in skill.resources}
        assert resources["readme.txt"].content == "hello"
        assert resources["assets/logo.bin"].content == b"\x00\x01"

    @pytest.mark.asyncio
    async def test_download_skill_zip_raises_when_skill_path_missing(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(200, json={"tree": [{"path": "skills/other/SKILL.md", "type": "blob"}]})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            downloader = GitHubDownloader(client)
            with pytest.raises(DownloaderError, match="Skill path not found"):
                await downloader.download_skill_zip("https://github.com/octo/demo", "skills/demo")

    @pytest.mark.asyncio
    async def test_download_skill_zip_falls_back_to_master(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/octo/demo/git/trees/main":
                return httpx.Response(404)
            if request.url.path == "/repos/octo/demo/git/trees/master":
                return httpx.Response(
                    200,
                    json={"tree": [{"path": "skills/demo/SKILL.md", "type": "blob"}]},
                )
            if request.url.path == "/octo/demo/master/skills/demo/SKILL.md":
                return httpx.Response(
                    200,
                    text="---\nname: Demo\ndescription: Downloaded skill\n---\nBody",
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            downloader = GitHubDownloader(client)
            zip_bytes = await downloader.download_skill_zip("https://github.com/octo/demo", "skills/demo")

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert zf.namelist() == ["demo/SKILL.md"]


class TestTopLevelDownloadSkillZip:
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

        class FakeDownloader:
            def __init__(self, client):
                assert client is sentinel_client

            async def download_skill_zip(self, repo_url: str, skill_path: str) -> bytes:
                assert repo_url == "https://github.com/octo/demo"
                assert skill_path == "skills/demo"
                return b"zip-bytes"

        monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)
        monkeypatch.setattr("dais_skills.downloader.GitHubDownloader", FakeDownloader)

        result = await download_skill_zip("https://github.com/octo/demo", "skills/demo")

        assert result == b"zip-bytes"
