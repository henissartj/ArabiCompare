# ArabiCompare

![Bannière](./banniere.png)

![Logo](./logo.png)

```text
    ___              __    _  ______                                   
   /   |  _________ _/ /_  (_)/ ____/___  ____ ___  ____  ____ ________
  / /| | / ___/ __ `/ __ \/ / /   / __ \/ __ `__ \/ __ \/ __ `/ ___/ _ \
 / ___ |/ /  / /_/ / /_/ / / /___/ /_/ / / / / / / /_/ / /_/ / /  /  __/
/_/  |_/_/   \__,_/_.___/_/\____/\____/_/ /_/ /_/ .___/\__,_/_/   \___/
                                                /_/                    
```

Outil console pour comparer intelligemment deux textes (arabe / français / bilingue), avec normalisation linguistique, diff coloré, mode translittération et exports.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

- Mode interactif :

```bash
python -m arabicompare
```

- Exemples rapides :
  - Comparer deux fichiers : choisissez “Comparer deux fichiers” dans le menu
  - Comparer deux blocs : choisissez “Comparer deux textes saisis”
  - Translittération : choisissez “Mode translittération”

## Notes

- Encodage attendu : UTF-8 (UTF-8 BOM accepté).
- Les exports sont proposés après l’affichage du résultat (TXT, MD, JSON).

## Démo (extrait)

```text
Lignes : 1
Différences réelles : 0
Différences ignorées : 1
ignored_diacritics
Différence ignorée (diacritiques)
```
