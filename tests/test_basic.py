"""Basic tests for dais-skills package."""

import pytest
from dais_skills import scan_repo, parse_source, Skill
from dais_skills.models import RepoTree, TreeEntry
from dais_skills.skill_discovery import (
    find_skill_md_paths,
    parse_skill_from_content,
    to_skill_slug,
)
from dais_skills.source_parser import sanitize_subpath


# --- Source Parser Tests ---


class TestSourceParser:
    """Test source string parsing."""

    def test_parse_shorthand(self):
        """Test owner/repo shorthand."""
        result = parse_source("vercel-labs/agent-skills")
        assert result.type == "github"
        assert result.owner_repo == "vercel-labs/agent-skills"
        assert result.url == "https://github.com/vercel-labs/agent-skills.git"
        assert result.ref is None
        assert result.subpath is None
        assert result.skill_filter is None

    def test_parse_with_skill_filter(self):
        """Test owner/repo@skill-name syntax."""
        result = parse_source("owner/repo@my-skill")
        assert result.owner_repo == "owner/repo"
        assert result.skill_filter == "my-skill"

    def test_parse_with_subpath(self):
        """Test owner/repo/path/to/subdir."""
        result = parse_source("owner/repo/skills/curated")
        assert result.owner_repo == "owner/repo"
        assert result.subpath == "skills/curated"

    def test_parse_github_url(self):
        """Test full GitHub URL."""
        result = parse_source("https://github.com/owner/repo")
        assert result.owner_repo == "owner/repo"
        assert result.url == "https://github.com/owner/repo.git"

    def test_parse_github_url_with_branch(self):
        """Test GitHub URL with tree/branch."""
        result = parse_source("https://github.com/owner/repo/tree/develop")
        assert result.owner_repo == "owner/repo"
        assert result.ref == "develop"

    def test_parse_github_url_with_branch_and_path(self):
        """Test GitHub URL with tree/branch/path."""
        result = parse_source("https://github.com/owner/repo/tree/main/skills")
        assert result.owner_repo == "owner/repo"
        assert result.ref == "main"
        assert result.subpath == "skills"

    def test_parse_with_fragment_ref(self):
        """Test #ref syntax."""
        result = parse_source("owner/repo#develop")
        assert result.owner_repo == "owner/repo"
        assert result.ref == "develop"

    def test_sanitize_subpath_safe(self):
        """Test safe subpath passes through."""
        result = sanitize_subpath("skills/curated")
        assert result == "skills/curated"

    def test_sanitize_subpath_unsafe(self):
        """Test path traversal is rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            sanitize_subpath("skills/../../../etc/passwd")

    def test_parse_invalid_source(self):
        """Test that unparseable source raises ValueError."""
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_source("not-a-valid-source")


# --- Skill Discovery Tests ---


class TestSkillDiscovery:
    """Test skill discovery logic."""

    def test_find_skill_md_paths_root(self):
        """Test finding root-level SKILL.md."""
        tree = RepoTree(
            sha="abc123",
            branch="main",
            tree=[
                TreeEntry(path="SKILL.md", type="blob", sha="def456"),
                TreeEntry(path="README.md", type="blob", sha="ghi789"),
            ]
        )
        paths = find_skill_md_paths(tree)
        assert "SKILL.md" in paths
        assert len(paths) == 1

    def test_find_skill_md_paths_priority_dirs(self):
        """Test finding skills in priority directories."""
        tree = RepoTree(
            sha="abc123",
            branch="main",
            tree=[
                TreeEntry(path="skills/react/SKILL.md", type="blob", sha="1"),
                TreeEntry(path="skills/vue/SKILL.md", type="blob", sha="2"),
                TreeEntry(path=".kiro/skills/testing/SKILL.md", type="blob", sha="3"),
                TreeEntry(path="random/deep/path/SKILL.md", type="blob", sha="4"),
            ]
        )
        paths = find_skill_md_paths(tree)
        # Should find priority dir skills, skip random deep path
        assert "skills/react/SKILL.md" in paths
        assert "skills/vue/SKILL.md" in paths
        assert ".kiro/skills/testing/SKILL.md" in paths
        assert "random/deep/path/SKILL.md" not in paths

    def test_find_skill_md_paths_with_subpath(self):
        """Test filtering by subpath."""
        tree = RepoTree(
            sha="abc123",
            branch="main",
            tree=[
                TreeEntry(path="skills/react/SKILL.md", type="blob", sha="1"),
                TreeEntry(path="other/vue/SKILL.md", type="blob", sha="2"),
            ]
        )
        paths = find_skill_md_paths(tree, subpath="skills")
        assert "skills/react/SKILL.md" in paths
        assert "other/vue/SKILL.md" not in paths

    def test_find_skill_md_paths_skip_dirs(self):
        """Test that skip directories are excluded."""
        tree = RepoTree(
            sha="abc123",
            branch="main",
            tree=[
                TreeEntry(path="skills/valid/test/SKILL.md", type="blob", sha="1"),
                TreeEntry(path="skills/node_modules/bad/SKILL.md", type="blob", sha="2"),
            ]
        )
        paths = find_skill_md_paths(tree)
        assert "skills/valid/test/SKILL.md" in paths
        assert "skills/node_modules/bad/SKILL.md" not in paths

    def test_parse_skill_from_content_valid(self):
        """Test parsing valid SKILL.md content."""
        content = """---
name: Test Skill
description: A test skill for unit testing
metadata:
  tags: [test, demo]
---

# Test Skill

Some content here.
"""
        skill = parse_skill_from_content(content, "skills/test/SKILL.md")
        assert skill is not None
        assert skill.name == "Test Skill"
        assert skill.description == "A test skill for unit testing"
        assert skill.repo_path == "skills/test/SKILL.md"
        assert skill.metadata == {"tags": ["test", "demo"]}

    def test_parse_skill_from_content_missing_name(self):
        """Test that missing name returns None."""
        content = """---
description: A skill without a name
---

Content.
"""
        skill = parse_skill_from_content(content, "test/SKILL.md")
        assert skill is None

    def test_parse_skill_from_content_missing_description(self):
        """Test that missing description returns None."""
        content = """---
name: Test Skill
---

Content.
"""
        skill = parse_skill_from_content(content, "test/SKILL.md")
        assert skill is None

    def test_parse_skill_from_content_internal_excluded(self):
        """Test that internal skills are excluded by default."""
        content = """---
name: Internal Skill
description: An internal skill
metadata:
  internal: true
---

Content.
"""
        skill = parse_skill_from_content(content, "test/SKILL.md")
        assert skill is None

    def test_parse_skill_from_content_internal_included(self):
        """Test that internal skills can be included."""
        content = """---
name: Internal Skill
description: An internal skill
metadata:
  internal: true
---

Content.
"""
        skill = parse_skill_from_content(content, "test/SKILL.md", include_internal=True)
        assert skill is not None
        assert skill.name == "Internal Skill"

    def test_to_skill_slug(self):
        """Test skill name to slug conversion."""
        assert to_skill_slug("React Best Practices") == "react-best-practices"
        assert to_skill_slug("Deploy_to_Vercel") == "deploy-to-vercel"
        assert to_skill_slug("Test@Skill#123") == "testskill123"
        assert to_skill_slug("  multiple   spaces  ") == "multiple-spaces"


# --- Integration Tests ---


@pytest.mark.asyncio(loop_scope="class")
class TestIntegration:
    """Integration tests requiring network access."""

    async def test_scan_repo_basic(self):
        """Test scanning a real repository."""
        skills = await scan_repo("vercel-labs/agent-skills")
        assert len(skills) > 0
        assert all(isinstance(s, Skill) for s in skills)
        assert all(s.name and s.description for s in skills)

    async def test_scan_repo_with_skill_filter(self):
        """Test scanning with skill filter."""
        skills = await scan_repo("vercel-labs/agent-skills@deploy-to-vercel")
        assert len(skills) >= 1
        assert any(s.name == "deploy-to-vercel" for s in skills)

    async def test_scan_repo_nonexistent(self):
        """Test scanning a non-existent repository."""
        skills = await scan_repo("nonexistent-user/nonexistent-repo-12345")
        assert len(skills) == 0
