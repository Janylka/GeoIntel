import json
from pathlib import Path

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_DIR = Path(__file__).parent

SUPPORTED_LANGS = ("ru", "ky", "en")
DEFAULT_LANG = "ru"


def _load_lang(lang: str) -> dict[str, str]:
    path = _DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data: dict[str, str] = json.load(f)
        return data


def _get_translations(lang: str) -> dict[str, str]:
    if lang not in _TRANSLATIONS:
        _TRANSLATIONS[lang] = _load_lang(lang)
    return _TRANSLATIONS[lang]


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: str) -> str:
    """
    Translate a key to a given language, falling back to Russian.
    Supports placeholder substitution via kwargs.
    """
    translations = _get_translations(lang)
    template = translations.get(key)

    if template is None:
        # Fallback to Russian
        translations_ru = _get_translations("ru")
        template = translations_ru.get(key, key)

    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
