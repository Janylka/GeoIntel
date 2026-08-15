import json
from pathlib import Path

I18N_DIR = Path(__file__).parent

LOCALES = {
    "ru": json.loads((I18N_DIR / "ru.json").read_text(encoding="utf-8")),
}