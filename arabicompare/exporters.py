from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .io_utils import ensure_parent_dir
from .models import CompareReport, LineDiffKind, TransliterationReport


def export_compare_txt(report: CompareReport, path: str | Path) -> Path:
    p = ensure_parent_dir(path)
    lines: list[str] = []
    s = report.summary
    lines.append("ArabiCompare - Résultat")
    lines.append(f"Lignes : {s.lines_compared}")
    lines.append(f"Différences réelles : {s.real_differences}")
    lines.append(f"Différences ignorées : {s.ignored_differences}")
    lines.append("")

    for d in report.diffs:
        if d.kind == LineDiffKind.EQUAL:
            continue
        a_no = "" if d.a_line_no is None else str(d.a_line_no)
        b_no = "" if d.b_line_no is None else str(d.b_line_no)
        lines.append(f"[{d.kind.value}] A:{a_no} B:{b_no} {d.reason or ''}".rstrip())
        if d.a_raw is not None:
            lines.append(f"A> {d.a_raw}")
        if d.b_raw is not None:
            lines.append(f"B> {d.b_raw}")
        lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def export_compare_md(report: CompareReport, path: str | Path) -> Path:
    p = ensure_parent_dir(path)
    s = report.summary
    out: list[str] = []
    out.append("# ArabiCompare - Résultat\n")
    out.append(f"- Lignes : **{s.lines_compared}**")
    out.append(f"- Différences réelles : **{s.real_differences}**")
    out.append(f"- Différences ignorées : **{s.ignored_differences}**\n")

    out.append("## Diff\n")
    for d in report.diffs:
        if d.kind == LineDiffKind.EQUAL:
            continue
        a_no = "" if d.a_line_no is None else str(d.a_line_no)
        b_no = "" if d.b_line_no is None else str(d.b_line_no)
        out.append(f"### {d.kind.value} (A:{a_no} / B:{b_no})")
        if d.reason:
            out.append(f"- Raison : {d.reason}")
        out.append("")
        if d.a_raw is not None:
            out.append("**A**")
            out.append("")
            out.append("```text")
            out.append(d.a_raw)
            out.append("```")
            out.append("")
        if d.b_raw is not None:
            out.append("**B**")
            out.append("")
            out.append("```text")
            out.append(d.b_raw)
            out.append("```")
            out.append("")

    p.write_text("\n".join(out), encoding="utf-8")
    return p


def export_compare_json(report: CompareReport, path: str | Path) -> Path:
    p = ensure_parent_dir(path)
    payload = asdict(report)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def export_translit_json(report: TransliterationReport, path: str | Path) -> Path:
    p = ensure_parent_dir(path)
    payload = asdict(report)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
