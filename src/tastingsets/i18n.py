"""Internationalisation helpers: UI strings, localized category names, country names."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from babel import Locale

DEFAULT_LANGUAGE = "de"
DEFAULT_LOCALES_DIR = Path(__file__).resolve().parents[2] / "locales"


class Translator:
    """Looks up UI strings: requested language, then ``de``, then the key itself."""

    def __init__(self, lang: str, locales_dir: Path | str = DEFAULT_LOCALES_DIR) -> None:
        self.lang = lang
        locales_dir = Path(locales_dir)
        self._strings = self._load(locales_dir, lang)
        self._fallback = self._load(locales_dir, DEFAULT_LANGUAGE) if lang != "de" else {}

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
    """Pick the name for ``lang``; fall back to ``de``, then to any available name."""
    if lang in names:
        return names[lang]
    if DEFAULT_LANGUAGE in names:
        return names[DEFAULT_LANGUAGE]
    return next(iter(names.values()))


def country_name(code: str, lang: str) -> str:
    """Localized country name for an ISO 3166-1 alpha-2 code (the code itself if unknown)."""
    return Locale.parse(lang).territories.get(code, code)
