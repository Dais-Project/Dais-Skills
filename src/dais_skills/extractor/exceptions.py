from dais_skills.exception import SkillException


class ExtractorException(SkillException):
    """Base error for skill archive extraction failures."""


class InvalidSkillArchiveError(ExtractorException):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SkillRootNotFoundError(InvalidSkillArchiveError):
    def __init__(self, message: str = "Skill root not found"):
        super().__init__(message)


class SkillMdNotFoundError(InvalidSkillArchiveError):
    def __init__(self, message: str = "SKILL.md not found"):
        super().__init__(message)


__all__ = [
    "ExtractorException",
    "InvalidSkillArchiveError",
    "SkillRootNotFoundError",
    "SkillMdNotFoundError",
]
