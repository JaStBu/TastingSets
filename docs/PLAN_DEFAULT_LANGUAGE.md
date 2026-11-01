# Umsetzungsplan: Standardsprache zentral definieren (Stufe 1) und Stufe 2 dokumentieren

> Verbindliche Vorgabe für die Umsetzung. Phasen in der angegebenen Reihenfolge abarbeiten.
> Code, Bezeichner, Kommentare und README sind auf Englisch; dieses Dokument und `docs/IMPLEMENTATION_PLAN.md` auf Deutsch.

## Ausgangslage

Die Standardsprache `"de"` ist heute an mehreren Stellen unabhängig voneinander festgelegt:

| Datei | Stelle | Heute |
| --- | --- | --- |
| `src/tastingsets/models.py` | Konstante | `REQUIRED_LANGUAGE = "de"`, genutzt in `_require_default_language` |
| `src/tastingsets/i18n.py` | Konstante | `DEFAULT_LANGUAGE = "de"`, genutzt in `available_languages` und `localized` |
| `src/tastingsets/i18n.py` | `Translator.__init__` | `if lang != "de"` (fest eingetragen, ignoriert die Konstante) |
| `src/tastingsets/stats.py` | `count_by_category`, `count_by_country`, `build_report` | je `lang: str = "de"` |
| `src/tastingsets/site/builder.py` | `build()` | Weiterleitung `/index.html` auf `languages[0]`, nicht auf die Standardsprache |
| Docstrings in `models.py`, `i18n.py` | Text | „`de` is required“, „then `de`“ |

Templates, CLI und Workflows enthalten keine feste Sprache.

**Ziel:** Die Standardsprache wird genau einmal definiert. Wer z.B. Spanisch als Standard will, ändert eine Zeile und legt `locales/es.json` an. Ein Test verhindert, dass wieder feste `"de"` in den Code kommen.

## Phase 1 – Zentrale Konstante

Schritte 2–5 hängen an Schritt 1 und sind untereinander unabhängig.

1. **Neue Datei `src/tastingsets/languages.py`**, ohne Imports:
   ```python
   """The default (primary) language of the project.

   It is required in every localized data field (``names``, ``description``), it is the
   fallback for localized content and UI strings, it must always be built, and ``/index.html``
   redirects to it. When changing it, ``locales/<language>.json`` must exist and all localized
   data fields must contain the new language.
   """

   DEFAULT_LANGUAGE = "de"
   ```
2. **`src/tastingsets/models.py`:**
   - Die Konstante `REQUIRED_LANGUAGE` entfernen.
   - `from tastingsets.languages import DEFAULT_LANGUAGE` importieren.
   - `_require_default_language` nutzt `DEFAULT_LANGUAGE` (Fehlermeldung unverändert im Format: `must contain the language '<lang>'`).
   - Kommentar über `LocalizedText`: `#: Text per language (``{"de": "...", "en": "..."}``); the default language is required.` Das Beispiel darf `"de"` enthalten, weil es in einem Kommentar steht und kein String-Literal ist.
   - Vorher prüfen, dass `REQUIRED_LANGUAGE` nirgends sonst verwendet wird (Suche in `src/` und `tests/`). Fundstellen ebenfalls auf `DEFAULT_LANGUAGE` umstellen.
3. **`src/tastingsets/i18n.py`:**
   - `DEFAULT_LANGUAGE = "de"` entfernen und stattdessen `from tastingsets.languages import DEFAULT_LANGUAGE` importieren. Damit funktioniert `from tastingsets.i18n import DEFAULT_LANGUAGE` weiterhin.
   - In `Translator.__init__`: `if lang != "de"` wird zu `if lang != DEFAULT_LANGUAGE`.
   - Docstrings: `Translator`: „Looks up UI strings: requested language, then the default language, then the key itself.“; `localized`: „Pick the name for ``lang``; fall back to the default language, then to any available name.“
   - `available_languages` bleibt inhaltlich unverändert.
4. **`src/tastingsets/stats.py`:**
   - `from tastingsets.languages import DEFAULT_LANGUAGE` importieren (Modulebene).
   - In `count_by_category`, `count_by_country` und `build_report` den Standardwert `lang: str = "de"` durch `lang: str = DEFAULT_LANGUAGE` ersetzen.
   - Die vorhandenen lokalen Imports aus `tastingsets.i18n` innerhalb der Funktionen nicht anfassen.
5. **`src/tastingsets/site/builder.py`, Funktion `build()`:**
   - `from tastingsets.languages import DEFAULT_LANGUAGE` importieren.
   - Direkt nach dem bestehenden Block, der `languages` festlegt (`if languages is None: ...` und `if not languages: raise ValueError(...)`), und **bevor irgendeine Datei geschrieben wird**, in dieser Reihenfolge prüfen:
     1. Existiert `Path(locales_dir) / f"{DEFAULT_LANGUAGE}.json"` nicht: `raise FileNotFoundError(f"locale file for default language '{DEFAULT_LANGUAGE}' not found: {path}")`.
     2. Ist `DEFAULT_LANGUAGE` nicht in `languages`: `raise ValueError(f"default language '{DEFAULT_LANGUAGE}' must be built (languages: {', '.join(languages)})")`.
   - Die Reihenfolge ist wichtig: Fehlt die Datei der Standardsprache, liefert `available_languages()` sie gar nicht, und ohne Prüfung 1 käme die weniger klare Meldung aus Prüfung 2.
   - Die Weiterleitung auf der Startseite: `{"target": f"{languages[0]}/"}` wird zu `{"target": f"{DEFAULT_LANGUAGE}/"}`.
   - Die Validierung der Daten (`validate` / `BuildError`) bleibt der erste Schritt in `build()`.

## Phase 2 – CLI

*Hängt an Schritt 5.*

6. **`src/tastingsets/cli.py`, `cmd_build`:** zusätzlich `except ValueError as exc:` → `print(f"error: {exc}", file=sys.stderr)` und `return 2`, analog zum bestehenden `FileNotFoundError`-Zweig. Die Option `--languages` bleibt unverändert.

## Phase 3 – Tests

*Hängt an Phase 1 und 2. Nach jeder Phase `uv run pytest` ausführen.*

Regel aus dem Projekt: Tests verwenden nie das echte `data/`. `locales/` und `src/` sind Code-Ressourcen und dürfen gelesen werden.

7. **`tests/test_i18n.py`:**
   - `test_real_locales_have_same_keys` ersetzen durch `test_all_locales_have_same_keys_as_default`: Für jede Datei in `DEFAULT_LOCALES_DIR.glob("*.json")` sind die Schlüssel gleich denen von `locales/<DEFAULT_LANGUAGE>.json`. Bei Abweichung die fehlenden bzw. überzähligen Schlüssel in der Assertion-Meldung nennen.
   - Neu `test_default_language_has_no_fallback`: Mit dem bestehenden Fixture `locales` liefert `Translator(DEFAULT_LANGUAGE, locales).t("missing") == "missing"`.
   - Neu `test_available_languages_puts_default_first`: In `tmp_path` die Dateien `fr.json`, `en.json` und `<DEFAULT_LANGUAGE>.json` anlegen (Inhalt `{}`). Erwartet: `[DEFAULT_LANGUAGE, "en", "fr"]`. Dateinamen nicht hart als `"de.json"` schreiben, sondern aus `DEFAULT_LANGUAGE` bilden.
8. **`tests/test_builder.py`:**
   - Neu `test_build_requires_default_language`: `build(..., languages=["en"])` wirft `ValueError` (`match="default language"`) und `out` existiert danach nicht.
   - Neu `test_build_requires_default_locale_file`: Locales-Ordner in `tmp_path` mit nur `en.json` (Inhalt `{}`). `build(..., languages=[DEFAULT_LANGUAGE, "en"], locales_dir=...)` wirft `FileNotFoundError` (`match="default language"`) und `out` existiert danach nicht.
   - Neu `test_redirect_points_to_default_language`: `build(..., languages=["en", DEFAULT_LANGUAGE])`; `out/index.html` enthält `url=/<DEFAULT_LANGUAGE>/`.
9. **`tests/test_cli.py`:** neu `test_build_without_default_language_exits_two`: `main(["build", "--data", str(data_dir), "--out", str(tmp_path / "dist"), "--languages", "en"]) == 2`, stderr enthält `default language`.
10. **Neue Datei `tests/test_languages.py`:**
    - `test_default_language_is_a_valid_locale`: `babel.Locale.parse(DEFAULT_LANGUAGE)` wirft nicht.
    - `test_default_locale_file_exists`: `(DEFAULT_LOCALES_DIR / f"{DEFAULT_LANGUAGE}.json").is_file()`.
    - `test_default_language_is_not_hardcoded`: Schutz-Test. Alle Dateien `src/tastingsets/**/*.py` außer `languages.py` mit `ast.parse` einlesen und per `ast.walk` jeden `ast.Constant`-Knoten melden, dessen Wert ein `str` und genau gleich `DEFAULT_LANGUAGE` ist. Erwartet: keine Funde. Die Assertion-Meldung nennt Datei und Zeilennummer (`node.lineno`) und den Hinweis „use tastingsets.languages.DEFAULT_LANGUAGE“. Den Pfad zu `src/tastingsets` über `Path(tastingsets.__file__).parent` bestimmen.
11. Alle übrigen Tests bleiben unverändert. Deutsche Erwartungswerte und `{"de": ...}` in Testdaten sind in Ordnung, sie liegen unter `tests/`, nicht unter `src/`.

## Phase 4 – Dokumentation

*Parallel zu Phase 3 möglich.*

12. **`README.md`, Abschnitt „Data model“:**
    - Tabellenzeile `data/categories/`: `` `names` (language → name, `de` required) `` wird zu `` `names` (language → name, default language required) ``.
    - Absatz „Groups (optional)“: `` `names` (language → name, `de` required) `` wird zu `` `names` (language → name, default language required) ``.
    - Direkt nach der Aufzählung unter dem Datenmodell (vor „### Validation“) einen neuen Unterabschnitt einfügen:
      ```markdown
      ### Languages

      The default language is defined once in `src/tastingsets/languages.py` (currently `de`). It is required in every localized field (`names`, `description`), it is the fallback for localized content and UI strings, it must always be built, and `/index.html` redirects to it. To use another default language (e.g. Spanish), change `DEFAULT_LANGUAGE`, add `locales/es.json` with the same keys as the other locale files, and add the language to all localized fields in `data/` (`uv run tastingsets validate` lists every affected document).
      ```
13. **`README.md`, Abschnitt „Architecture and outlook“:** am Ende einen neuen Absatz anfügen:
    ```markdown
    **Configurable default language (not implemented yet).** Today the default language is a constant in `src/tastingsets/languages.py`; changing it means changing code. If the project is used as a package by others, it could become a setting instead:

    - *Where:* the setting belongs to the data contract, not to the build, because changing it invalidates existing data. Candidates are a file next to the collections, e.g. `data/settings.json` (not loaded as a collection), or `[tool.tastingsets] default_language` in `pyproject.toml`. With MongoDB, it would be a settings document.
    - *Validation:* Pydantic receives the language via the validation context (`model_validate(..., context={"default_language": ...})`, read in the validator via `ValidationInfo.context`) instead of the module constant. `JsonRepository` and later `MongoRepository` pass it through.
    - *Other layers:* `i18n`, `stats` and the site builder receive the language as a parameter instead of importing the constant. Because the constant is used in one place only, this is a contained change.
    - *Switching:* existing data must be migrated; `validate` shows every document that lacks the new default language.

    Implement this only when there is a concrete need.
    ```
14. **`docs/IMPLEMENTATION_PLAN.md`:**
    - Phase 2a, Punkt A: „`de` Pflicht“ wird zu „Standardsprache Pflicht“.
    - Abschnitt „Decisions“, Punkt zu den optionalen Gruppen: „(`de` Pflicht)“ wird zu „(Standardsprache Pflicht)“.
    - Abschnitt „Decisions“: neuen Punkt anfügen: „Standardsprache: genau einmal definiert in `src/tastingsets/languages.py` (`DEFAULT_LANGUAGE`). Sie ist Pflicht in mehrsprachigen Datenfeldern, Rückfall für Inhalte und Oberflächentexte, muss immer gebaut werden und ist Ziel der Weiterleitung von `/index.html`. Ein Test verhindert feste Sprach-Strings in `src/`.“
    - Abschnitt „Further Considerations“: neuen, fortlaufend nummerierten Punkt anfügen: „**Einstellbare Standardsprache (Stufe 2):** siehe README, Abschnitt „Architecture and outlook“. Umsetzung erst bei konkretem Bedarf.“

## Relevant files

- `src/tastingsets/languages.py` (neu)
- `src/tastingsets/models.py`
- `src/tastingsets/i18n.py`
- `src/tastingsets/stats.py`
- `src/tastingsets/site/builder.py`
- `src/tastingsets/cli.py`
- `tests/test_i18n.py`, `tests/test_builder.py`, `tests/test_cli.py`, `tests/test_languages.py` (neu)
- `README.md`, `docs/IMPLEMENTATION_PLAN.md`

## Verification

1. `uv run ruff format --check`, `uv run ruff check` und `uv run pytest` sind grün.
2. `grep -rn '"de"' src/` findet nur `src/tastingsets/languages.py`. (Treffer in Kommentaren wie dem Beispiel über `LocalizedText` sind erlaubt; der Schutz-Test prüft nur echte String-Literale.)
3. `uv run tastingsets validate` meldet 0 Fehler.
4. `uv run tastingsets build --out dist --languages en de` endet mit Exit-Code 0, und `dist/index.html` leitet auf `/de/` weiter.
5. `uv run tastingsets build --out dist --languages en` endet mit Exit-Code 2 und der Meldung `error: default language 'de' must be built ...` auf stderr.
6. Optionaler manueller Probelauf (danach rückgängig machen, nicht committen): `DEFAULT_LANGUAGE = "en"` setzen; `uv run tastingsets build --out dist` leitet auf `/en/` weiter. Die Tests schlagen dabei erwartbar fehl, weil sie deutsche Texte prüfen.

## Decisions

- Eigenes Modul `languages.py` ohne Abhängigkeiten, damit das Datenmodell nicht von `i18n` abhängt.
- Nur ein Name: `DEFAULT_LANGUAGE`. `REQUIRED_LANGUAGE` entfällt, weil es dasselbe Konzept ist.
- Die Statistik-Funktionen behalten einen Standardwert, nämlich `DEFAULT_LANGUAGE`.
- Die Standardsprache muss immer gebaut werden; die Weiterleitung zeigt immer auf sie.
- Fehlt `locales/<DEFAULT_LANGUAGE>.json`, bricht der Build mit klarer Meldung ab. Ein Test stellt sicher, dass alle Übersetzungsdateien dieselben Schlüssel haben wie die der Standardsprache.
- **Nicht enthalten:** Stufe 2 umsetzen (Konfiguration, Validierungskontext), Daten auf eine andere Sprache umstellen, Tests von deutschen Texten unabhängig machen, Reihenfolge der Sprachumschaltung im Seitenkopf ändern.

## Further Considerations

1. **Schutz-Test per `ast`:** Er meldet nur String-Literale, die genau der Standardsprache entsprechen. Ein künftiger legitimer Gebrauch muss `DEFAULT_LANGUAGE` verwenden oder eine Ausnahmeliste im Test bekommen. Start ohne Ausnahmeliste.
2. **Reihenfolge der Sprachumschaltung:** Sie folgt der Reihenfolge von `languages`; bei `--languages en de` steht Englisch vorne. Bewusst so gelassen, rein optisch.
