from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ArabiCompareError(Exception):
    pass


class FileReadError(ArabiCompareError):
    pass


class UserInputError(ArabiCompareError):
    pass


@dataclass(frozen=True, slots=True)
class TextSource:
    label: str
    text: str


def read_text_file(path: str | Path) -> TextSource:
    p = Path(path)
    if not p.exists():
        raise FileReadError(f"Fichier introuvable : {p}")
    if p.is_dir():
        raise FileReadError(f"Chemin invalide (dossier) : {p}")

    raw = p.read_bytes()

    for encoding in ("utf-8-sig", "utf-8"):
        try:
            text = raw.decode(encoding, errors="strict")
            return TextSource(label=str(p), text=text)
        except UnicodeDecodeError:
            continue

    raise FileReadError(
        f"Impossible de lire {p} en UTF-8 (encodage non valide ou fichier corrompu)."
    )


def read_multiline_from_console(prompt: str) -> str:
    print(prompt)
    print("(Terminer par une ligne contenant uniquement : EOF)")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "EOF":
            break
        lines.append(line)
    return "\n".join(lines)


def ensure_parent_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
