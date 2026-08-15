import json
from pathlib import Path

I18N_DIR = Path(__file__).parent

TRANSLATIONS = {
    "ru": json.loads((I18N_DIR / "ru.json").read_text()),
    "ky": json.loads((I18N_DIR / "ky.json").read_text()),
    "en": json.loads((I18N_DIR / "en.json").read_text()),
}

DEFAULT_LANG = "ru"

def t(key: str, lang: str) -> str:
    """
    Translates a key into the specified language.
    Falls back to Russian if the key or language is not found.
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key,
           TRANSLATIONS[DEFAULT_LANG].get(key, key))
