from dataclasses import dataclass
from typing import Literal


@dataclass
class BaseResource:
    relative: str


@dataclass
class TextResource(BaseResource):
    content: str
    type: Literal["text"] = "text"


@dataclass
class BinaryResource(BaseResource):
    content: bytes
    type: Literal["binary"] = "binary"


type SkillResource = TextResource | BinaryResource


def _is_binary_content(content: bytes) -> bool:
    if not content:
        return False

    if b"\x00" in content:
        return True

    text_bytes = set(range(32, 127)) | {9, 10, 12, 13}
    utf8_bom = b"\xef\xbb\xbf"
    sample = content[3:] if content.startswith(utf8_bom) else content
    if not sample:
        return False

    non_text = sum(byte not in text_bytes for byte in sample)
    return (non_text / len(sample)) > 0.3


def create_from_bytes(relative: str, content: bytes) -> SkillResource:
    if _is_binary_content(content):
        return BinaryResource(relative=relative, content=content)

    return TextResource(
        relative=relative,
        content=content.decode("utf-8-sig", errors="replace"),
    )


__all__ = [
    "BaseResource",
    "TextResource",
    "BinaryResource",
    "SkillResource",
    "create_from_bytes",
]
