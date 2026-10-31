import json

import pytest

from tastingsets.i18n import Translator, country_name, localized


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


def test_real_locales_have_same_keys():
    de = Translator("de")._strings
    en = Translator("en")._strings
    assert set(de) == set(en)


def test_localized():
    names = {"de": "Grappa", "en": "Grappa EN"}
    assert localized(names, "en") == "Grappa EN"
    assert localized(names, "fr") == "Grappa"
    assert localized({"it": "Grappa IT"}, "fr") == "Grappa IT"


def test_country_name():
    assert country_name("GB", "de") == "Vereinigtes Königreich"
    assert country_name("GB", "en") == "United Kingdom"
    assert country_name("QQ", "en") == "QQ"
