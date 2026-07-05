"""End-to-end smoke test that hits real GitHub services.

Runs the full pipeline against https://github.com/anthropics/skills:
    scan_repo -> download_skill_zip -> Skill.from_zip

Marked with `smoke`; skip in offline environments via `pytest -m "not smoke"`.
"""

import io
import zipfile

import pytest

from dais_skills.downloader import download_skill_zip
from dais_skills.extractor import Skill
from dais_skills.scanner import scan_repo


REPO_URL = "https://github.com/anthropics/skills"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_scan_download_extract_pipeline():
    skills = await scan_repo(REPO_URL)
    assert skills, "expected at least one skill to be discovered"
    print("Scanned skills: ", skills)

    first = skills[0]
    assert first.path
    assert first.name
    assert first.description

    zip_bytes = await download_skill_zip(REPO_URL, first.path)
    assert zip_bytes, "expected non-empty zip payload"

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        skill = Skill.from_zip(zf)

    assert skill.name
    assert skill.description
    print("Downloaded skill: ", skill)
