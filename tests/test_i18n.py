import json

import pytest

from tastingsets.i18n import (
    DEFAULT_LOCALES_DIR,
    Translator,
    available_languages,
    country_name,
    localized,
)
from tastingsets.languages import DEFAULT_LANGUAGE


@pytest.fixture
def locales(tmp_path):
    (tmp_path / "de.json").write_text(json.dumps({"a": "Eins", "b": "Zwei {n}"}), encoding="utf-8")
    (tmp_path / "en.json").write_text(json.dumps({"a": "One"}), encoding="utf-8")
    return tmp_path


def test_translator_uses_language_and_falls_back(locales):
    en = Translator("en", locales)
    assert en.t("a") == "One"
    assert en("b", n=2) == "Zwei 2"  # falls back to de
    assert en.t("missing") == "missing"  # falls back to key


def test_translator_missing_language_file(locales):
    with pytest.raises(FileNotFoundError):
        Translator("fr", locales)


def test_all_locales_have_same_keys_as_default():
    default_keys = set(Translator(DEFAULT_LANGUAGE)._strings)
    for path in sorted(DEFAULT_LOCALES_DIR.glob("*.json")):
        keys = set(Translator(path.stem)._strings)
        assert keys == default_keys, (
            f"{path.name}: missing {sorted(default_keys - keys)}, "
            f"unexpected {sorted(keys - default_keys)}"
        )


def test_default_language_has_no_fallback(tmp_path):
    (tmp_path / f"{DEFAULT_LANGUAGE}.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    translator = Translator(DEFAULT_LANGUAGE, tmp_path)
    assert translator.t("a") == "A"
    assert translator.t("missing") == "missing"


def test_available_languages_puts_default_first(tmp_path):
    for name in ("fr", "en", DEFAULT_LANGUAGE):
        (tmp_path / f"{name}.json").write_text("{}", encoding="utf-8")
    assert available_languages(tmp_path) == [
        DEFAULT_LANGUAGE,
        *sorted({"en", "fr"} - {DEFAULT_LANGUAGE}),
    ]


def test_localized():
    names = {"de": "Grappa", "en": "Grappa EN"}
    assert localized(names, "en") == "Grappa EN"
    assert localized(names, "fr") == "Grappa"
    assert localized({"it": "Grappa IT"}, "fr") == "Grappa IT"


def test_country_name():
    assert country_name("GB", "de") == "Vereinigtes Königreich"
    assert country_name("GB", "en") == "United Kingdom"
    assert country_name("QQ", "en") == "QQ"
