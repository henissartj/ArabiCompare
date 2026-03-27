from __future__ import annotations

import re
import unicodedata

from .models import ArabicOrthographyMode, NormalizationOptions


_ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"
)
_TATWEEL = "\u0640"

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_QUOTE_DASH_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u00AB": '"',
        "\u00BB": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00A0": " ",
        "\u2009": " ",
        "\u202F": " ",
    }
)


def normalize_text(text: str, options: NormalizationOptions) -> str:
    if options.unicode_nfkc:
        text = unicodedata.normalize("NFKC", text)

    if options.unify_quotes_dashes:
        text = text.translate(_QUOTE_DASH_TRANSLATION)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if options.trim_lines:
        text = "\n".join(line.strip() for line in text.split("\n"))

    if options.normalize_whitespace:
        text = re.sub(r"[ \t]+", " ", text)

    if options.collapse_internal_spaces:
        text = re.sub(r"\s+", " ", text)

    return text


def normalize_arabic(text: str, options: NormalizationOptions) -> str:
    if options.remove_tatweel:
        text = text.replace(_TATWEEL, "")

    if options.remove_arabic_diacritics:
        text = _ARABIC_DIACRITICS_RE.sub("", text)

    if options.unify_arabic_digits:
        text = text.translate(_ARABIC_DIGITS)

    mode = options.orthography_mode
    if mode != ArabicOrthographyMode.OFF:
        text = _normalize_arabic_orthography(text, aggressive=mode == ArabicOrthographyMode.AGGRESSIVE)

    if options.unify_ya_maqsurah:
        text = text.replace("ى", "ي")

    if options.unify_ta_marbuta:
        text = text.replace("ة", "ه")

    return text


def normalize_for_compare(text: str, options: NormalizationOptions) -> str:
    text = normalize_text(text, options)
    text = normalize_arabic(text, options)
    return text


def arabic_skeleton(text: str) -> str:
    base = unicodedata.normalize("NFKC", text)
    base = base.translate(_QUOTE_DASH_TRANSLATION)
    base = base.replace(_TATWEEL, "")
    base = _ARABIC_DIACRITICS_RE.sub("", base)
    base = _normalize_arabic_orthography(base, aggressive=True)
    base = base.replace("ى", "ي")
    base = re.sub(r"[ \t]+", " ", base).strip()
    return base


def is_arabic_heavy(text: str, threshold: float = 0.3) -> bool:
    if not text:
        return False

    arabic = 0
    letters = 0
    for ch in text:
        if ch.isalpha():
            letters += 1
        code = ord(ch)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0x08A0 <= code <= 0x08FF:
            arabic += 1
    if letters == 0:
        return False
    return (arabic / letters) >= threshold


def _normalize_arabic_orthography(text: str, aggressive: bool) -> str:
    translation: dict[str, str] = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ء": "",
        "ؤ": "و" if aggressive else "ؤ",
        "ئ": "ي" if aggressive else "ئ",
    }
    if aggressive:
        translation.update(
            {
                "ۀ": "ه",
                "ٮ": "ب",
                "ك": "ك",
                "گ": "ك",
                "پ": "ب",
                "چ": "ج",
                "ڤ": "ف",
            }
        )

    return text.translate(str.maketrans(translation))