import ast
from pathlib import Path

from babel import Locale

import tastingsets
from tastingsets.i18n import DEFAULT_LOCALES_DIR
from tastingsets.languages import DEFAULT_LANGUAGE


def test_default_language_is_a_valid_locale():
    Locale.parse(DEFAULT_LANGUAGE)


def test_default_locale_file_exists():
    assert (DEFAULT_LOCALES_DIR / f"{DEFAULT_LANGUAGE}.json").is_file()


def test_default_language_is_not_hardcoded():
    """The default language is defined once; no other module may repeat it as a string."""
    package_dir = Path(tastingsets.__file__).parent
    findings = []
    for path in sorted(package_dir.rglob("*.py")):
        if path.name == "languages.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value == DEFAULT_LANGUAGE
            ):
                findings.append(f"{path.relative_to(package_dir)}:{node.lineno}")
    assert findings == [], (
        f"hard-coded default language {DEFAULT_LANGUAGE!r} found, "
        f"use tastingsets.languages.DEFAULT_LANGUAGE: {findings}"
    )
