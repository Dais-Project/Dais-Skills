class ExtractorException(Exception): ...


class InvalidSkillArchiveError(ExtractorException):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


__all__ = [
    "ExtractorException",
    "InvalidSkillArchiveError",
]
