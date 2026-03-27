from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Iterable

from .models import (
    CompareOptions,
    InlineChunk,
    LineDiff,
    LineDiffKind,
    Summary,
    CompareReport,
)
from .normalize import normalize_for_compare, normalize_text, arabic_skeleton


_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


def compare_texts(text_a: str, text_b: str, options: CompareOptions) -> CompareReport:
    a_lines_raw = text_a.splitlines()
    b_lines_raw = text_b.splitlines()

    a_lines_norm = [normalize_for_compare(line, options.normalization) for line in a_lines_raw]
    b_lines_norm = [normalize_for_compare(line, options.normalization) for line in b_lines_raw]

    sm = difflib.SequenceMatcher(a=a_lines_norm, b=b_lines_norm, autojunk=False)
    diffs: list[LineDiff] = []

    a_no = 1
    b_no = 1

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                a_raw = a_lines_raw[i1 + k]
                b_raw = b_lines_raw[j1 + k]
                a_norm = a_lines_norm[i1 + k]
                b_norm = b_lines_norm[j1 + k]
                kind, reason = _classify_line_difference(a_raw, b_raw, a_norm, b_norm, options)
                diffs.append(
                    LineDiff(
                        a_line_no=a_no,
                        b_line_no=b_no,
                        a_raw=a_raw,
                        b_raw=b_raw,
                        a_norm=a_norm,
                        b_norm=b_norm,
                        kind=kind,
                        reason=reason,
                        word_chunks=_inline_chunks(a_norm, b_norm, by_words=True),
                    )
                )
                a_no += 1
                b_no += 1
            continue

        if tag == "replace":
            a_block = list(range(i1, i2))
            b_block = list(range(j1, j2))
            max_len = max(len(a_block), len(b_block))
            for idx in range(max_len):
                ai = a_block[idx] if idx < len(a_block) else None
                bj = b_block[idx] if idx < len(b_block) else None

                a_raw = a_lines_raw[ai] if ai is not None else None
                b_raw = b_lines_raw[bj] if bj is not None else None
                a_norm = a_lines_norm[ai] if ai is not None else None
                b_norm = b_lines_norm[bj] if bj is not None else None

                if ai is None:
                    diffs.append(
                        LineDiff(
                            a_line_no=None,
                            b_line_no=b_no,
                            a_raw=None,
                            b_raw=b_raw,
                            a_norm=None,
                            b_norm=b_norm,
                            kind=LineDiffKind.INSERTED,
                            reason="Ligne ajoutée",
                        )
                    )
                    b_no += 1
                    continue

                if bj is None:
                    diffs.append(
                        LineDiff(
                            a_line_no=a_no,
                            b_line_no=None,
                            a_raw=a_raw,
                            b_raw=None,
                            a_norm=a_norm,
                            b_norm=None,
                            kind=LineDiffKind.DELETED,
                            reason="Ligne supprimée",
                        )
                    )
                    a_no += 1
                    continue

                kind, reason = _classify_line_difference(a_raw, b_raw, a_norm, b_norm, options)
                diffs.append(
                    LineDiff(
                        a_line_no=a_no,
                        b_line_no=b_no,
                        a_raw=a_raw,
                        b_raw=b_raw,
                        a_norm=a_norm,
                        b_norm=b_norm,
                        kind=kind,
                        reason=reason,
                        word_chunks=_inline_chunks(a_norm, b_norm, by_words=True),
                    )
                )
                a_no += 1
                b_no += 1
            continue

        if tag == "delete":
            for ai in range(i1, i2):
                diffs.append(
                    LineDiff(
                        a_line_no=a_no,
                        b_line_no=None,
                        a_raw=a_lines_raw[ai],
                        b_raw=None,
                        a_norm=a_lines_norm[ai],
                        b_norm=None,
                        kind=LineDiffKind.DELETED,
                        reason="Ligne supprimée",
                    )
                )
                a_no += 1
            continue

        if tag == "insert":
            for bj in range(j1, j2):
                diffs.append(
                    LineDiff(
                        a_line_no=None,
                        b_line_no=b_no,
                        a_raw=None,
                        b_raw=b_lines_raw[bj],
                        a_norm=None,
                        b_norm=b_lines_norm[bj],
                        kind=LineDiffKind.INSERTED,
                        reason="Ligne ajoutée",
                    )
                )
                b_no += 1
            continue

    summary = _summarize(diffs)
    return CompareReport(options=options, diffs=tuple(diffs), summary=summary)


def _summarize(diffs: Iterable[LineDiff]) -> Summary:
    lines = 0
    real = 0
    ignored = 0
    for d in diffs:
        lines += 1
        if d.kind in (LineDiffKind.IGNORED_DIACRITICS, LineDiffKind.IGNORED_TYPO):
            ignored += 1
        elif d.kind != LineDiffKind.EQUAL:
            real += 1
    return Summary(lines_compared=lines, real_differences=real, ignored_differences=ignored)


def _inline_chunks(a: str | None, b: str | None, by_words: bool) -> tuple[InlineChunk, ...]:
    if a is None or b is None:
        return ()

    if by_words:
        a_seq = _tokenize(a)
        b_seq = _tokenize(b)
    else:
        a_seq = list(a)
        b_seq = list(b)

    sm = difflib.SequenceMatcher(a=a_seq, b=b_seq, autojunk=False)
    chunks: list[InlineChunk] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a_part = _join_tokens(a_seq[i1:i2], by_words=by_words)
        b_part = _join_tokens(b_seq[j1:j2], by_words=by_words)
        chunks.append(InlineChunk(kind=tag, a=a_part, b=b_part))
    return tuple(chunks)


def _join_tokens(tokens: list[str], by_words: bool) -> str:
    if not tokens:
        return ""
    if not by_words:
        return "".join(tokens)
    out = ""
    for t in tokens:
        if not out:
            out = t
            continue
        if _needs_space_between(out[-1], t[0]):
            out += " " + t
        else:
            out += t
    return out


def _needs_space_between(prev: str, nxt: str) -> bool:
    if prev.isspace() or nxt.isspace():
        return False
    if prev.isalnum() and nxt.isalnum():
        return True
    return False


_TOKEN_RE = re.compile(r"\w+|[^\w\s]+", flags=re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _classify_line_difference(
    a_raw: str,
    b_raw: str,
    a_norm: str,
    b_norm: str,
    options: CompareOptions,
) -> tuple[LineDiffKind, str | None]:
    if a_norm == b_norm:
        if a_raw == b_raw:
            return LineDiffKind.EQUAL, None

        a_no_d = _strip_diacritics(a_raw)
        b_no_d = _strip_diacritics(b_raw)
        if a_no_d == b_no_d:
            return LineDiffKind.IGNORED_DIACRITICS, "Différence ignorée (diacritiques)"

        a_txt = normalize_text(a_raw, options.normalization)
        b_txt = normalize_text(b_raw, options.normalization)
        if a_txt == b_txt:
            return LineDiffKind.IGNORED_TYPO, "Différence ignorée (typographie Unicode)"

        return LineDiffKind.IGNORED_TYPO, "Différence ignorée (normalisation)"

    a_skel = arabic_skeleton(a_raw)
    b_skel = arabic_skeleton(b_raw)
    if a_skel == b_skel:
        return LineDiffKind.DIFFERENT, "Différence réelle (variante orthographique possible)"

    return LineDiffKind.DIFFERENT, "Différence réelle"


def _strip_diacritics(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return _ARABIC_DIACRITICS_RE.sub("", text)
