"""Shared language settings for the bilingual README.

README.md is the English profile; README.pt-BR.md is the Portuguese copy. Every card
is rendered in both languages, and Portuguese assets live in a `pt/` folder next to
their English counterparts (assets/x.svg -> assets/pt/x.svg).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("en", "pt")
READMES = {"en": ROOT / "README.md", "pt": ROOT / "README.pt-BR.md"}

MONTHS_PT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
# Section and folder titles used by the featured cards and the repository tree.
GROUPS_PT = {
    "AI & Automation": "IA & Automação", "Web, Data & Research": "Web, Dados & Pesquisa", "Games & 3D": "Jogos & 3D",
    "AI & Tools": "IA & Ferramentas", "Academic": "Acadêmico", "Community": "Comunidade",
}
WEEKDAYS_PT = {
    "Monday": "segunda", "Tuesday": "terça", "Wednesday": "quarta", "Thursday": "quinta",
    "Friday": "sexta", "Saturday": "sábado", "Sunday": "domingo",
}


def localized(path, lang):
    """Where the `lang` version of an English asset path lives."""
    return path if lang == "en" else path.parent / lang / path.name


def group_title(title, lang):
    return GROUPS_PT.get(title, title) if lang == "pt" else title


def number(value, lang):
    """1234 -> "1,234" in English and "1.234" in Portuguese."""
    text = f"{value:,}"
    return text if lang == "en" else text.replace(",", ".")


def plural(value, singular, plural_form, lang):
    return f"{number(value, lang)} {singular if value == 1 else plural_form}"
