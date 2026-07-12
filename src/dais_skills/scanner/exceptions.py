from dais_skills.exception import SkillException


class ScannerError(SkillException):
    """Base error for skill scanning failures."""


class InvalidRepoUrlError(ScannerError):
    def __init__(self, url: str, reason: str | None = None):
        self.url = url
        super().__init__(reason or f"Invalid repository URL: {url}")


class RepositoryTreeFetchError(ScannerError):
    def __init__(self, message: str):
        super().__init__(message)


__all__ = [
    "ScannerError",
    "InvalidRepoUrlError",
    "RepositoryTreeFetchError",
]
