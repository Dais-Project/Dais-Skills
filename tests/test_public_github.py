import pytest

from dais_skills.public.github import GitHubError, GitHubRepo


class TestGitHubRepoFromUrl:
    def test_parse_plain_repo_url(self):
        repo = GitHubRepo.from_url("https://github.com/octo/demo")

        assert repo.owner == "octo"
        assert repo.repo == "demo"
        assert repo.ref is None

    def test_parse_tree_url(self):
        repo = GitHubRepo.from_url("https://github.com/octo/demo/tree/main")

        assert repo.owner == "octo"
        assert repo.repo == "demo"
        assert repo.ref == "main"

    def test_parse_tree_url_with_slashes_in_ref(self):
        repo = GitHubRepo.from_url("https://github.com/octo/demo/tree/feature/test-branch")

        assert repo.owner == "octo"
        assert repo.repo == "demo"
        assert repo.ref == "feature/test-branch"

    def test_reject_non_github_url(self):
        with pytest.raises(GitHubError, match="Unsupported GitHub repository URL"):
            GitHubRepo.from_url("https://gitlab.com/octo/demo")
