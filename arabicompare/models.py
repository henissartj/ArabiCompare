from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class CompareGranularity(str, Enum):
    LINES = "lines"
    WORDS = "words"
    BOTH = "both"


class ArabicOrthographyMode(str, Enum):
    OFF = "off"
    BASIC = "basic"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True, slots=True)
class NormalizationOptions:
    unicode_nfkc: bool = True
    normalize_whitespace: bool = True
    trim_lines: bool = True
    collapse_internal_spaces: bool = False
    unify_quotes_dashes: bool = True

    remove_arabic_diacritics: bool = True
    remove_tatweel: bool = True
    orthography_mode: ArabicOrthographyMode = ArabicOrthographyMode.BASIC
    unify_ya_maqsurah: bool = True
    unify_ta_marbuta: bool = False
    unify_arabic_digits: bool = False


@dataclass(frozen=True, slots=True)
class CompareOptions:
    normalization: NormalizationOptions = field(default_factory=NormalizationOptions)
    granularity: CompareGranularity = CompareGranularity.BOTH
    rtl_display: bool = False
    context_chars: int = 40


class LineDiffKind(str, Enum):
    EQUAL = "equal"
    IGNORED_DIACRITICS = "ignored_diacritics"
    IGNORED_TYPO = "ignored_typography"
    DIFFERENT = "different"
    INSERTED = "inserted"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class InlineChunk:
    kind: Literal["equal", "delete", "insert", "replace"]
    a: str
    b: str


@dataclass(frozen=True, slots=True)
class LineDiff:
    a_line_no: int | None
    b_line_no: int | None
    a_raw: str | None
    b_raw: str | None
    a_norm: str | None
    b_norm: str | None
    kind: LineDiffKind
    reason: str | None = None
    word_chunks: tuple[InlineChunk, ...] = ()


@dataclass(frozen=True, slots=True)
class TransliterationMismatch:
    token_index: int
    arabic_token: str
    expected: str
    provided: str


@dataclass(frozen=True, slots=True)
class Summary:
    lines_compared: int
    real_differences: int
    ignored_differences: int


@dataclass(frozen=True, slots=True)
class CompareReport:
    options: CompareOptions
    diffs: tuple[LineDiff, ...]
    summary: Summary
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransliterationReport:
    arabic_text: str
    transliteration_text: str
    mismatches: tuple[TransliterationMismatch, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
