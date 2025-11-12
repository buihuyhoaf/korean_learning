"""Utility helpers for working with Hangul syllables and jamo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

CHOSEONG = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]

JUNGSEONG = [
    "ㅏ",
    "ㅐ",
    "ㅑ",
    "ㅒ",
    "ㅓ",
    "ㅔ",
    "ㅕ",
    "ㅖ",
    "ㅗ",
    "ㅘ",
    "ㅙ",
    "ㅚ",
    "ㅛ",
    "ㅜ",
    "ㅝ",
    "ㅞ",
    "ㅟ",
    "ㅠ",
    "ㅡ",
    "ㅢ",
    "ㅣ",
]

JONGSEONG = [
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]

TargetCategory = Literal["syllable", "choseong", "jungseong", "jongseong", "unknown"]


@dataclass(frozen=True)
class HangulSplit:
    """Represents the decomposition of a Hangul character."""

    choseong: str
    jungseong: str
    jongseong: str

    @property
    def components(self) -> tuple[str, str, str]:
        return self.choseong, self.jungseong, self.jongseong


def is_hangul_syllable(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return 0xAC00 <= code <= 0xD7A3


def split_hangul(char: str) -> HangulSplit:
    if not char:
        return HangulSplit("", "", "")

    char = char[0]

    if is_hangul_syllable(char):
        code = ord(char) - 0xAC00
        choseong_index = code // 588
        jungseong_index = (code % 588) // 28
        jongseong_index = code % 28
        return HangulSplit(
            CHOSEONG[choseong_index],
            JUNGSEONG[jungseong_index],
            JONGSEONG[jongseong_index],
        )

    if char in CHOSEONG:
        return HangulSplit(char, "", "")

    if char in JUNGSEONG:
        return HangulSplit("", char, "")

    if char in JONGSEONG:
        return HangulSplit("", "", char)

    return HangulSplit("", "", "")


def classify_target_char(char: Optional[str]) -> TargetCategory:
    if not char:
        return "unknown"

    char = char[0]
    if is_hangul_syllable(char):
        return "syllable"
    if char in CHOSEONG:
        return "choseong"
    if char in JUNGSEONG:
        return "jungseong"
    if char in JONGSEONG:
        return "jongseong"
    return "unknown"
