from pathlib import Path

import pytest

from tastingsets.cli import main
from tastingsets.languages import DEFAULT_LANGUAGE
from tastingsets.repository.json_repository import JsonRepository
from tastingsets.site.builder import BuildError, build, normalize_base_url

FIXTURES = Path(__file__).parent / "fixtures" / "data"


def test_normalize_base_url():
    assert normalize_base_url("") == "/"
    assert normalize_base_url("/") == "/"
    assert normalize_base_url("TastingSets") == "/TastingSets/"
    assert normalize_base_url("/TastingSets") == "/TastingSets/"


def test_build_writes_expected_files(data_dir, tmp_path):
    out = tmp_path / "dist"
    written = build(JsonRepository(data_dir), out)
    assert (out / "index.html").is_file()
    assert (out / "de" / "index.html").is_file()
    assert (out / "de" / "stats" / "index.html").is_file()
    assert (out / "de" / "sets" / "advent-2025" / "index.html").is_file()
    assert (out / "de" / "sets" / "advent-2026" / "index.html").is_file()
    assert (out / "static" / "style.css").is_file()
    assert out / "de" / "index.html" in written


def test_default_build_includes_all_locale_files(data_dir, tmp_path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    source_locales = Path(__file__).parents[1] / "locales"
    for language in ("de", "fr"):
        source = source_locales / ("en.json" if language == "fr" else "de.json")
        contents = source.read_text(encoding="utf-8")
        (locales_dir / f"{language}.json").write_text(contents, encoding="utf-8")

    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out, locales_dir=locales_dir)

    assert (out / "de" / "index.html").is_file()
    assert (out / "fr" / "index.html").is_file()
    assert not (out / "en" / "index.html").exists()
    assert "url=/de/" in (out / "index.html").read_text(encoding="utf-8")


def test_build_requires_default_language(data_dir, tmp_path):
    out = tmp_path / "dist"
    with pytest.raises(ValueError, match="default language"):
        build(JsonRepository(data_dir), out, languages=["en"])
    assert not out.exists()


def test_build_requires_default_locale_file(data_dir, tmp_path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    (locales_dir / "en.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "dist"
    with pytest.raises(FileNotFoundError, match="default language"):
        build(
            JsonRepository(data_dir),
            out,
            languages=[DEFAULT_LANGUAGE, "en"],
            locales_dir=locales_dir,
        )
    assert not out.exists()


def test_redirect_points_to_default_language(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out, languages=["en", DEFAULT_LANGUAGE])
    assert f"url=/{DEFAULT_LANGUAGE}/" in (out / "index.html").read_text(encoding="utf-8")


def test_set_page_lists_members_with_details(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out)
    html = (out / "de" / "sets" / "advent-2025" / "index.html").read_text(encoding="utf-8")
    assert "Advent 2025" in html
    assert 'id="member-1"' in html and 'id="member-2"' in html
    assert "Ardbeg 10" in html
    assert "Vereinigtes Königreich" in html  # localized country
    assert "Secret Distillery" in html  # distillery without entry
    assert "46,0 %" in html  # German number format
    assert "cask strength" in html
    assert 'href="https://example.org/secret"' in html


def test_set_name_and_notes_are_localized(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out, languages=["de", "en"])
    de = (out / "de" / "sets" / "advent-2025" / "index.html").read_text(encoding="utf-8")
    en = (out / "en" / "sets" / "advent-2025" / "index.html").read_text(encoding="utf-8")
    assert "Advent 2025" in de and "Advent 2025" in en  # no English name -> fallback
    assert "cask strength" in de and "cask strength" in en  # notes fall back too
    index_en = (out / "en" / "index.html").read_text(encoding="utf-8")
    assert "Advent 2026" in index_en


def test_stats_page_content(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out)
    html = (out / "de" / "stats" / "index.html").read_text(encoding="utf-8")
    assert "Flaschen pro Brennerei" in html
    assert "advent-2025/1, advent-2026/2, advent-2026/3" in html
    assert "unbekannt" in html


def test_base_url_is_used_in_links(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out, base_url="/TastingSets")
    index = (out / "de" / "index.html").read_text(encoding="utf-8")
    assert (out / "en" / "index.html").is_file()
    assert 'href="/TastingSets/de/sets/advent-2025/"' in index
    assert 'href="/TastingSets/static/style.css"' in index
    root = (out / "index.html").read_text(encoding="utf-8")
    assert "url=/TastingSets/de/" in root


def test_multiple_languages(data_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(data_dir), out, languages=["de", "en"])
    en = (out / "en" / "sets" / "advent-2025" / "index.html").read_text(encoding="utf-8")
    assert "United Kingdom" in en
    assert "46.0 %" in en
    assert 'href="/de/sets/advent-2025/"' in en  # language switch


def test_html_is_escaped(data_dir, tmp_path):
    from conftest import SPIRITS, make_data_dir

    evil = {**SPIRITS[0], "name": "<script>alert(1)</script>"}
    root = make_data_dir(tmp_path / "evil", spirits=[evil, *SPIRITS[1:]])
    build(JsonRepository(root), tmp_path / "dist")
    html = (tmp_path / "dist" / "de" / "sets" / "advent-2025" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_build_aborts_on_errors(tmp_path):
    out = tmp_path / "dist"
    with pytest.raises(BuildError) as excinfo:
        build(JsonRepository(FIXTURES), out)
    assert any(i.code == "UNKNOWN_SPIRIT" for i in excinfo.value.issues)
    assert not out.exists()


def test_cli_build(data_dir, tmp_path, capsys):
    out = tmp_path / "dist"
    assert main(["build", "--data", str(data_dir), "--out", str(out), "--base-url", "/x/"]) == 0
    assert (out / "de" / "index.html").is_file()
    assert (out / "en" / "index.html").is_file()
    assert "wrote" in capsys.readouterr().out


def test_cli_build_fails_on_invalid_data(tmp_path, capsys):
    assert main(["build", "--data", str(FIXTURES), "--out", str(tmp_path / "dist")]) == 1
    assert "site not generated" in capsys.readouterr().err


def test_cli_build_missing_data_dir(tmp_path):
    assert main(["build", "--data", str(tmp_path / "nope"), "--out", str(tmp_path / "d")]) == 2
