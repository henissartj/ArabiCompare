from __future__ import annotations

import difflib
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .ascii_art import ARABICOMPARE_ASCII
from .models import CompareReport, LineDiff, LineDiffKind
from .normalize import is_arabic_heavy


_RLE = "\u202B"
_PDF = "\u202C"


def print_header(console: Console) -> None:
    console.print(Text(ARABICOMPARE_ASCII, style="bold cyan"))
    console.print(Text("Comparaison linguistique (arabe / français / bilingue)", style="dim"))


def render_report(
    report: CompareReport,
    console: Console,
    *,
    show_equal: bool = False,
    max_lines: int | None = None,
) -> None:
    _render_summary(report, console)

    diffs = report.diffs
    if not show_equal:
        diffs = tuple(d for d in diffs if d.kind != LineDiffKind.EQUAL)

    if max_lines is not None:
        diffs = diffs[: max(0, max_lines)]

    if not diffs:
        console.print(Panel(Text("Aucune différence détectée.", style="bold green"), title="Résultat"))
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("A", style="dim", width=4, justify="right")
    table.add_column("Texte A", overflow="fold")
    table.add_column("B", style="dim", width=4, justify="right")
    table.add_column("Texte B", overflow="fold")
    table.add_column("Type", style="dim", width=18)

    for d in diffs:
        a_no = "" if d.a_line_no is None else str(d.a_line_no)
        b_no = "" if d.b_line_no is None else str(d.b_line_no)

        a_txt, b_txt = _render_line_pair(d, rtl_display=report.options.rtl_display)
        label = _kind_label(d.kind, d.reason)

        table.add_row(a_no, a_txt, b_no, b_txt, label)

    console.print(Panel(table, title="Diff"))


def _render_summary(report: CompareReport, console: Console) -> None:
    s = report.summary
    norm = report.options.normalization
    lines = [
        f"Lignes : {s.lines_compared}",
        f"Différences réelles : {s.real_differences}",
        f"Différences ignorées : {s.ignored_differences}",
        "",
        "Normalisation :",
        f"- Diacritiques : {'ON' if norm.remove_arabic_diacritics else 'OFF'}",
        f"- Orthographe arabe : {norm.orthography_mode.value}",
        f"- ى→ي : {'ON' if norm.unify_ya_maqsurah else 'OFF'}",
        f"- ة→ه : {'ON' if norm.unify_ta_marbuta else 'OFF'}",
        f"- Unicode NFKC : {'ON' if norm.unicode_nfkc else 'OFF'}",
    ]
    console.print(Panel(Text("\n".join(lines)), title="Résumé", expand=False))


def _render_line_pair(d: LineDiff, *, rtl_display: bool) -> tuple[Text, Text]:
    if d.kind == LineDiffKind.INSERTED:
        b_raw = d.b_raw or ""
        b = _wrap_rtl_text(Text(b_raw, style="bold green"), b_raw, rtl_display=rtl_display)
        return Text("", style="dim"), b
    if d.kind == LineDiffKind.DELETED:
        a_raw = d.a_raw or ""
        a = _wrap_rtl_text(Text(a_raw, style="bold red"), a_raw, rtl_display=rtl_display)
        return a, Text("", style="dim")

    a_raw = d.a_raw or ""
    b_raw = d.b_raw or ""

    if d.kind == LineDiffKind.EQUAL:
        return (
            _wrap_rtl_text(Text(a_raw), a_raw, rtl_display=rtl_display),
            _wrap_rtl_text(Text(b_raw), b_raw, rtl_display=rtl_display),
        )

    if d.kind in (LineDiffKind.IGNORED_DIACRITICS, LineDiffKind.IGNORED_TYPO):
        a_t, b_t = _diff_text(a_raw, b_raw, strong=False)
        a_t.stylize("dim")
        b_t.stylize("dim")
        return (
            _wrap_rtl_text(a_t, a_raw, rtl_display=rtl_display),
            _wrap_rtl_text(b_t, b_raw, rtl_display=rtl_display),
        )

    a_t, b_t = _diff_words(a_raw, b_raw, strong=True)
    return (
        _wrap_rtl_text(a_t, a_raw, rtl_display=rtl_display),
        _wrap_rtl_text(b_t, b_raw, rtl_display=rtl_display),
    )


def _diff_text(a: str, b: str, *, strong: bool) -> tuple[Text, Text]:
    a_chars = list(a)
    b_chars = list(b)
    sm = difflib.SequenceMatcher(a=a_chars, b=b_chars, autojunk=False)

    a_out = Text()
    b_out = Text()

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a_part = "".join(a_chars[i1:i2])
        b_part = "".join(b_chars[j1:j2])

        if tag == "equal":
            a_out.append(a_part)
            b_out.append(b_part)
            continue

        if tag == "delete":
            a_out.append(a_part, style="bold red" if strong else "red")
            continue

        if tag == "insert":
            b_out.append(b_part, style="bold green" if strong else "green")
            continue

        if tag == "replace":
            if a_part:
                a_out.append(a_part, style="bold red" if strong else "red")
            if b_part:
                b_out.append(b_part, style="bold green" if strong else "green")

    return a_out, b_out


_TOKEN_RE = re.compile(r"\w+|[^\w\s]+", flags=re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _diff_words(a: str, b: str, *, strong: bool) -> tuple[Text, Text]:
    a_tokens = _tokenize(a)
    b_tokens = _tokenize(b)
    sm = difflib.SequenceMatcher(a=a_tokens, b=b_tokens, autojunk=False)

    a_out = Text()
    b_out = Text()

    a_prev = ""
    b_prev = ""

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a_part = a_tokens[i1:i2]
        b_part = b_tokens[j1:j2]

        if tag == "equal":
            a_prev = _append_tokens(a_out, a_part, prev=a_prev, style=None)
            b_prev = _append_tokens(b_out, b_part, prev=b_prev, style=None)
            continue

        if tag == "delete":
            a_prev = _append_tokens(a_out, a_part, prev=a_prev, style="bold red" if strong else "red")
            continue

        if tag == "insert":
            b_prev = _append_tokens(b_out, b_part, prev=b_prev, style="bold green" if strong else "green")
            continue

        if tag == "replace":
            if a_part:
                a_prev = _append_tokens(a_out, a_part, prev=a_prev, style="bold red" if strong else "red")
            if b_part:
                b_prev = _append_tokens(b_out, b_part, prev=b_prev, style="bold green" if strong else "green")

    return a_out, b_out


def _append_tokens(out: Text, tokens: list[str], *, prev: str, style: str | None) -> str:
    for t in tokens:
        if prev and _needs_space_between(prev[-1], t[0]):
            out.append(" ")
        out.append(t, style=style)
        prev += (" " if prev and _needs_space_between(prev[-1], t[0]) else "") + t
    return prev


def _needs_space_between(prev: str, nxt: str) -> bool:
    if prev.isspace() or nxt.isspace():
        return False
    if prev.isalnum() and nxt.isalnum():
        return True
    return False


def _kind_label(kind: LineDiffKind, reason: str | None) -> Text:
    base = kind.value
    if reason:
        base = f"{base}\n{reason}"
    style = {
        LineDiffKind.EQUAL: "dim",
        LineDiffKind.IGNORED_DIACRITICS: "yellow",
        LineDiffKind.IGNORED_TYPO: "yellow",
        LineDiffKind.DIFFERENT: "bold",
        LineDiffKind.INSERTED: "green",
        LineDiffKind.DELETED: "red",
    }[kind]
    return Text(base, style=style)


def _wrap_rtl_text(text: Text, raw: str, *, rtl_display: bool) -> Text:
    if not rtl_display:
        return text
    if not is_arabic_heavy(raw):
        return text
    return Text.assemble((_RLE, ""), text, (_PDF, ""))
