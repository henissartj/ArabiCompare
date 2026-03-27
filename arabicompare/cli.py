from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .compare import compare_texts
from .diff_render import print_header, render_report
from .exporters import export_compare_json, export_compare_md, export_compare_txt, export_translit_json
from .io_utils import FileReadError, UserInputError, read_multiline_from_console, read_text_file
from .models import ArabicOrthographyMode, CompareOptions, NormalizationOptions
from .translit import compare_arabic_with_transliteration


def main(argv: list[str] | None = None) -> int:
    console = Console()
    print_header(console)

    args = _parse_args(argv)
    try:
        if args.command == "compare-files":
            _run_compare_files(console, args.file_a, args.file_b, args)
            return 0
        if args.command == "compare-text":
            _run_compare_text(console, args.text_a, args.text_b, args)
            return 0
        if args.command == "translit":
            _run_translit(console, args.arabic, args.latin, args)
            return 0
        _interactive_menu(console)
        return 0
    except (FileReadError, UserInputError) as e:
        console.print(Panel(Text(str(e), style="bold red"), title="Erreur"))
        return 2


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="arabicompare", add_help=True)
    sub = p.add_subparsers(dest="command")

    c1 = sub.add_parser("compare-files", help="Comparer deux fichiers texte UTF-8")
    c1.add_argument("file_a")
    c1.add_argument("file_b")

    c2 = sub.add_parser("compare-text", help="Comparer deux blocs texte (arguments)")
    c2.add_argument("text_a")
    c2.add_argument("text_b")

    c3 = sub.add_parser("translit", help="Comparer arabe ↔ translittération")
    c3.add_argument("arabic")
    c3.add_argument("latin")

    for sp in (c1, c2, c3):
        sp.add_argument("--rtl", action="store_true", help="Améliorer l’affichage RTL (si terminal compatible)")
        sp.add_argument("--show-equal", action="store_true", help="Afficher aussi les lignes identiques")
        sp.add_argument("--export-base", default=None, help="Chemin de base pour exporter (sans extension)")
        sp.add_argument(
            "--orthography",
            choices=[m.value for m in ArabicOrthographyMode],
            default=ArabicOrthographyMode.BASIC.value,
        )
        sp.add_argument("--keep-diacritics", action="store_true", help="Ne pas supprimer les diacritiques")
        sp.add_argument("--no-ya", action="store_true", help="Ne pas unifier ى→ي")
        sp.add_argument("--ta-marbuta", action="store_true", help="Unifier ة→ه")

    return p.parse_args(argv)


def _interactive_menu(console: Console) -> None:
    while True:
        console.print()
        console.print(
            Panel(
                Text(
                    "\n".join(
                        [
                            "1) Comparer deux fichiers",
                            "2) Comparer deux textes saisis",
                            "3) Mode translittération (arabe ↔ latin)",
                            "4) Quitter",
                        ]
                    )
                ),
                title="Menu",
            )
        )
        choice = Prompt.ask("Choix", choices=["1", "2", "3", "4"], default="1")
        if choice == "4":
            return
        if choice == "1":
            file_a = Prompt.ask("Chemin du fichier A")
            file_b = Prompt.ask("Chemin du fichier B")
            opts, show_equal = _prompt_options(console)
            src_a = read_text_file(file_a)
            src_b = read_text_file(file_b)
            report = compare_texts(src_a.text, src_b.text, opts)
            render_report(report, console, show_equal=show_equal)
            _prompt_export_compare(console, report)
            continue
        if choice == "2":
            a = read_multiline_from_console("Texte A :")
            b = read_multiline_from_console("Texte B :")
            opts, show_equal = _prompt_options(console)
            report = compare_texts(a, b, opts)
            render_report(report, console, show_equal=show_equal)
            _prompt_export_compare(console, report)
            continue
        if choice == "3":
            arabic = read_multiline_from_console("Texte arabe :")
            latin = read_multiline_from_console("Translittération :")
            rtl = Confirm.ask("Activer un mode d’affichage RTL (si terminal compatible) ?", default=False)
            report = compare_arabic_with_transliteration(arabic, latin)
            _render_translit(console, report, rtl_display=rtl)
            _prompt_export_translit(console, report)
            continue


def _prompt_options(console: Console) -> tuple[CompareOptions, bool]:
    console.print(Panel(Text("Options de normalisation et d’affichage"), title="Options"))
    remove_d = Confirm.ask("Supprimer les diacritiques arabes ?", default=True)
    ortho = Prompt.ask(
        "Mode orthographique arabe",
        choices=[m.value for m in ArabicOrthographyMode],
        default=ArabicOrthographyMode.BASIC.value,
    )
    unify_ya = Confirm.ask("Unifier ى→ي ?", default=True)
    unify_ta = Confirm.ask("Unifier ة→ه ?", default=False)
    rtl = Confirm.ask("Activer un mode d’affichage RTL (si terminal compatible) ?", default=False)
    show_equal = Confirm.ask("Afficher aussi les lignes identiques ?", default=False)

    norm = NormalizationOptions(
        remove_arabic_diacritics=remove_d,
        orthography_mode=ArabicOrthographyMode(ortho),
        unify_ya_maqsurah=unify_ya,
        unify_ta_marbuta=unify_ta,
    )
    opts = CompareOptions(normalization=norm, rtl_display=rtl)
    return opts, show_equal


def _prompt_export_compare(console: Console, report) -> None:
    if not Confirm.ask("Exporter le résultat ?", default=False):
        return

    base = Prompt.ask("Chemin de base (sans extension)", default="arabicompare_result")
    base_path = Path(base)
    did_any = False

    if Confirm.ask("Exporter en .txt ?", default=True):
        p = export_compare_txt(report, base_path.with_suffix(".txt"))
        console.print(Text(f"Écrit : {p}", style="green"))
        did_any = True
    if Confirm.ask("Exporter en .md ?", default=False):
        p = export_compare_md(report, base_path.with_suffix(".md"))
        console.print(Text(f"Écrit : {p}", style="green"))
        did_any = True
    if Confirm.ask("Exporter en .json ?", default=True):
        p = export_compare_json(report, base_path.with_suffix(".json"))
        console.print(Text(f"Écrit : {p}", style="green"))
        did_any = True

    if not did_any:
        console.print(Text("Aucun export sélectionné.", style="yellow"))


def _prompt_export_translit(console: Console, report) -> None:
    if not Confirm.ask("Exporter le résultat translittération en .json ?", default=False):
        return
    base = Prompt.ask("Chemin du fichier .json", default="arabicompare_translit.json")
    p = export_translit_json(report, base)
    console.print(Text(f"Écrit : {p}", style="green"))


def _render_translit(console: Console, report, *, rtl_display: bool) -> None:
    mismatches = report.mismatches
    if not mismatches:
        console.print(Panel(Text("Aucune incohérence détectée (comparaison tolérante).", style="bold green"), title="Translittération"))
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Arabe", overflow="fold")
    table.add_column("Attendu", overflow="fold")
    table.add_column("Fourni", overflow="fold")

    for m in mismatches[:500]:
        arab = _maybe_rtl(m.arabic_token, rtl_display)
        table.add_row(str(m.token_index), arab, m.expected, m.provided)

    more = ""
    if len(mismatches) > 500:
        more = f"\n\nAffichage limité à 500 incohérences sur {len(mismatches)}."
    console.print(Panel(Text("Incohérences détectées." + more), title="Translittération"))
    console.print(table)


_RLE = "\u202B"
_PDF = "\u202C"


def _maybe_rtl(text: str, rtl_display: bool) -> str:
    if not rtl_display:
        return text
    if not text:
        return text
    return f"{_RLE}{text}{_PDF}"


def _options_from_args(args: argparse.Namespace) -> tuple[CompareOptions, bool, Path | None]:
    norm = NormalizationOptions(
        remove_arabic_diacritics=not args.keep_diacritics,
        orthography_mode=ArabicOrthographyMode(args.orthography),
        unify_ya_maqsurah=not args.no_ya,
        unify_ta_marbuta=args.ta_marbuta,
    )
    opts = CompareOptions(normalization=norm, rtl_display=bool(args.rtl))
    export_base = None if args.export_base is None else Path(args.export_base)
    return opts, bool(args.show_equal), export_base


def _run_compare_files(console: Console, file_a: str, file_b: str, args: argparse.Namespace) -> None:
    opts, show_equal, export_base = _options_from_args(args)
    src_a = read_text_file(file_a)
    src_b = read_text_file(file_b)
    report = compare_texts(src_a.text, src_b.text, opts)
    render_report(report, console, show_equal=show_equal)
    if export_base is not None:
        export_compare_txt(report, export_base.with_suffix(".txt"))
        export_compare_md(report, export_base.with_suffix(".md"))
        export_compare_json(report, export_base.with_suffix(".json"))


def _run_compare_text(console: Console, text_a: str, text_b: str, args: argparse.Namespace) -> None:
    opts, show_equal, export_base = _options_from_args(args)
    report = compare_texts(text_a, text_b, opts)
    render_report(report, console, show_equal=show_equal)
    if export_base is not None:
        export_compare_txt(report, export_base.with_suffix(".txt"))
        export_compare_md(report, export_base.with_suffix(".md"))
        export_compare_json(report, export_base.with_suffix(".json"))


def _run_translit(console: Console, arabic: str, latin: str, args: argparse.Namespace) -> None:
    rtl = bool(args.rtl)
    report = compare_arabic_with_transliteration(arabic, latin)
    _render_translit(console, report, rtl_display=rtl)
    if args.export_base is not None:
        export_translit_json(report, Path(args.export_base).with_suffix(".json"))
