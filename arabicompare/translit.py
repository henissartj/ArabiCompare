from __future__ import annotations

import difflib
import re
import unicodedata

from .models import TransliterationMismatch, TransliterationReport
from .normalize import arabic_skeleton


_ARABIC_WORD_RE = re.compile(r"[\u0600-\u06FF]+", flags=re.UNICODE)
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u02BC\u02BE']+", flags=re.UNICODE)

_AR2LAT: dict[str, str] = {
    "ا": "ā",
    "أ": "a",
    "إ": "i",
    "آ": "ā",
    "ء": "ʾ",
    "ؤ": "ʾ",
    "ئ": "ʾ",
    "ب": "b",
    "ت": "t",
    "ث": "th",
    "ج": "j",
    "ح": "ḥ",
    "خ": "kh",
    "د": "d",
    "ذ": "dh",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "sh",
    "ص": "ṣ",
    "ض": "ḍ",
    "ط": "ṭ",
    "ظ": "ẓ",
    "ع": "ʿ",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "w",
    "ي": "y",
    "ى": "ā",
    "ة": "a",
    "ﻻ": "lā",
    "لا": "lā",
}

_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL = "\u0640"


def compare_arabic_with_transliteration(arabic_text: str, transliteration_text: str) -> TransliterationReport:
    arabic_tokens = _tokenize_arabic(arabic_text)
    expected_tokens = [_arabic_token_to_translit(t) for t in arabic_tokens]
    provided_tokens = _tokenize_latin(transliteration_text)

    expected_skel = [_latin_consonant_skeleton(t) for t in expected_tokens]
    provided_skel = [_latin_consonant_skeleton(t) for t in provided_tokens]

    sm = difflib.SequenceMatcher(a=expected_skel, b=provided_skel, autojunk=False)
    mismatches: list[TransliterationMismatch] = []

    token_index = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            token_index += (i2 - i1)
            continue

        if tag == "delete":
            for i in range(i1, i2):
                mismatches.append(
                    TransliterationMismatch(
                        token_index=token_index,
                        arabic_token=arabic_tokens[i],
                        expected=expected_tokens[i],
                        provided="",
                    )
                )
                token_index += 1
            continue

        if tag == "insert":
            for j in range(j1, j2):
                mismatches.append(
                    TransliterationMismatch(
                        token_index=token_index,
                        arabic_token="",
                        expected="",
                        provided=provided_tokens[j],
                    )
                )
            continue

        if tag == "replace":
            exp_range = list(range(i1, i2))
            prov_range = list(range(j1, j2))
            max_len = max(len(exp_range), len(prov_range))
            for k in range(max_len):
                i = exp_range[k] if k < len(exp_range) else None
                j = prov_range[k] if k < len(prov_range) else None
                mismatches.append(
                    TransliterationMismatch(
                        token_index=token_index,
                        arabic_token="" if i is None else arabic_tokens[i],
                        expected="" if i is None else expected_tokens[i],
                        provided="" if j is None else provided_tokens[j],
                    )
                )
                token_index += 1
            continue

    return TransliterationReport(
        arabic_text=arabic_text,
        transliteration_text=transliteration_text,
        mismatches=tuple(mismatches),
        metadata={
            "expected_tokens": expected_tokens,
            "provided_tokens": provided_tokens,
        },
    )


def _tokenize_arabic(text: str) -> list[str]:
    return _ARABIC_WORD_RE.findall(text)


def _tokenize_latin(text: str) -> list[str]:
    norm = unicodedata.normalize("NFKC", text).lower()
    norm = norm.replace("\u2019", "'").replace("\u02BC", "'")
    return _LATIN_TOKEN_RE.findall(norm)


def _arabic_token_to_translit(token: str) -> str:
    token = unicodedata.normalize("NFKC", token)
    token = token.replace(_TATWEEL, "")
    token = _ARABIC_DIACRITICS_RE.sub("", token)

    skel = arabic_skeleton(token)
    out: list[str] = []
    for ch in skel:
        out.append(_AR2LAT.get(ch, ""))
    return "".join(out) or token


_LATIN_NORMALIZE = str.maketrans(
    {
        "ā": "a",
        "ī": "i",
        "ū": "u",
        "ḥ": "h",
        "ṣ": "s",
        "ḍ": "d",
        "ṭ": "t",
        "ẓ": "z",
        "ʿ": "",
        "ʾ": "",
        "’": "",
        "'": "",
        "-": "",
    }
)


def _latin_skeleton(token: str) -> str:
    norm = unicodedata.normalize("NFKD", token.lower())
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    norm = norm.translate(_LATIN_NORMALIZE)
    norm = re.sub(r"[^a-z]", "", norm)
    return norm


def _latin_consonant_skeleton(token: str) -> str:
    skel = _latin_skeleton(token)
    return re.sub(r"[aeiou]", "", skel)
