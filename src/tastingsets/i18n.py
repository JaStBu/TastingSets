"""Internationalisation helpers: UI strings, localized category names, country names."""

from __future__ import annotations

import gettext
import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import pycountry
from babel import Locale

from tastingsets.languages import DEFAULT_LANGUAGE

DEFAULT_LOCALES_DIR = Path(__file__).resolve().parents[2] / "locales"


def available_languages(locales_dir: Path | str = DEFAULT_LOCALES_DIR) -> list[str]:
    languages = sorted(path.stem for path in Path(locales_dir).glob("*.json"))
    if DEFAULT_LANGUAGE in languages:
        languages.remove(DEFAULT_LANGUAGE)
        languages.insert(0, DEFAULT_LANGUAGE)
    return languages


class Translator:
    """Looks up UI strings: requested language, then the default language, then the key itself."""

    def __init__(self, lang: str, locales_dir: Path | str = DEFAULT_LOCALES_DIR) -> None:
        self.lang = lang
        locales_dir = Path(locales_dir)
        self._strings = self._load(locales_dir, lang)
        self._fallback = (
            self._load(locales_dir, DEFAULT_LANGUAGE) if lang != DEFAULT_LANGUAGE else {}
        )

    @staticmethod
    def _load(locales_dir: Path, lang: str) -> dict[str, str]:
        path = locales_dir / f"{lang}.json"
        if not path.is_file():
            raise FileNotFoundError(f"locale file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def t(self, key: str, **values: object) -> str:
        text = self._strings.get(key)
        if text is None:
            text = self._fallback.get(key, key)
        return text.format(**values) if values else text

    __call__ = t


def localized(names: Mapping[str, str], lang: str) -> str:
    """Pick the name for ``lang``; fall back to the default language, then to any name."""
    if lang in names:
        return names[lang]
    if DEFAULT_LANGUAGE in names:
        return names[DEFAULT_LANGUAGE]
    return next(iter(names.values()))


@cache
def _subdivision_translations(lang: str) -> gettext.NullTranslations:
    return gettext.translation("iso3166-2", pycountry.LOCALES_DIR, languages=[lang], fallback=True)


def country_name(code: str, lang: str) -> str:
    """Localized name for an ISO 3166-1 alpha-2 or ISO 3166-2 code (the code if unknown)."""
    if "-" in code:
        subdivision = pycountry.subdivisions.get(code=code)
        if subdivision is None:
            return code
        return _subdivision_translations(lang).gettext(subdivision.name)
    return Locale.parse(lang).territories.get(code, code)
