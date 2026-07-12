from dais_skills.exception import SkillException


class DownloaderError(SkillException):
    """Base error for skill download failures."""


class InvalidRepoUrlError(DownloaderError):
    def __init__(self, url: str, reason: str | None = None):
        self.url = url
        super().__init__(reason or f"Invalid repository URL: {url}")


class InvalidSkillPathError(DownloaderError):
    def __init__(self, raw_path: str, reason: str):
        self.raw_path = raw_path
        self.reason = reason
        super().__init__(reason)


class SkillPathNotFoundError(DownloaderError):
    def __init__(self, skill_path: str):
        self.skill_path = skill_path
        super().__init__(f"Skill path not found: {skill_path}")


class SkillTreeFetchError(DownloaderError):
    def __init__(self, message: str):
        super().__init__(message)


class SkillFileDownloadError(DownloaderError):
    def __init__(self, path: str, message: str | None = None):
        self.path = path
        super().__init__(message or f"Failed to download skill file: {path}")


__all__ = [
    "DownloaderError",
    "InvalidRepoUrlError",
    "InvalidSkillPathError",
    "SkillPathNotFoundError",
    "SkillTreeFetchError",
    "SkillFileDownloadError",
]
