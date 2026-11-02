# Umsetzungsplan: Regionen-Statistik (generisch, in der Seite für Schottland)

> Verbindliche Vorgabe für die Umsetzung. Phasen in der angegebenen Reihenfolge abarbeiten.
> Code, Bezeichner, Kommentare und README sind auf Englisch; dieses Dokument und `docs/IMPLEMENTATION_PLAN.md` auf Deutsch.
> **Dieser Plan ist temporär und wird nach der Umsetzung gelöscht.** Alles, was dauerhaft gelten soll (Entscheidungen, Annahmen, Grenzen), muss danach in `docs/IMPLEMENTATION_PLAN.md` bzw. `README.md` stehen. Kein Code, kein Test und kein Dokument darf auf diese Datei verweisen.

## Ziel und Umfang

Es kommt eine neue Statistik „Flaschen pro Region“ dazu. Sie zählt die Flaschen nach dem Freitextfeld `Distillery.region` (z.B. `Islay`, `Speyside`).

**Statistik-Code (generisch):**
- Die Zählung lässt sich auf ein Land einschränken (exakter Ländercode wie bei `count_by_country`, z.B. `GB-SCT`) oder länderübergreifend ausführen (`country=None`).
- Regionen werden ohne Groß-/Kleinschreibung verglichen: `Islay`, `islay` und `ISLAY` sind ein Eintrag.
- Eine Region gehört immer zu ihrem Land. `GB-SCT`/`Highland` und `US`/`Highland` sind zwei verschiedene Einträge, auch länderübergreifend.
- Beschriftung der Zeilen:
  - Länderspezifisch nur die Region (z.B. `Islay`), denn das Land steht in der Überschrift.
  - Länderübergreifend „<lokalisierter Ländername>, <Region>“ (z.B. `Schottland, Islay` / `Scotland, Islay`).
- Für welche Länder die Seite eine Regionen-Tabelle zeigt, legt die Konstante `REGION_STATS_COUNTRIES` in `stats.py` fest. Ein Eintrag `None` steht für die länderübergreifende Tabelle.

**HTML-Ausgabe (vorerst nur Schottland):**
- `REGION_STATS_COUNTRIES = (SCOTLAND,)` mit `SCOTLAND = "GB-SCT"`.
- Der Titel kommt aus **einem einzigen** Locale-Schlüssel `stats.by_region` („Flaschen pro Region“ / „Bottles per region“). Ist ein Land gesetzt, ergänzt das Template dynamisch ` (<lokalisierter Ländername>)` über `country_name`. So steht „Flaschen pro Region (Schottland)“ bzw. „Bottles per region (Scotland)“ da, länderübergreifend nur „Flaschen pro Region“. Für weitere Länder ist kein neuer Locale-Schlüssel und keine Template-Änderung nötig, nur ein weiterer Eintrag in `REGION_STATS_COUNTRIES`.
- Die Tabellen stehen im Statistik-Raster direkt nach „Flaschen pro Land“, in der Reihenfolge von `REGION_STATS_COUNTRIES`.
- Eine Regionen-Tabelle erscheint nur, wenn die Auswahl (ein Set bzw. alle Sets) mindestens eine Flasche aus dem jeweiligen Land enthält; für Schottland heißt das: mindestens einen Member aus Schottland. Die länderübergreifende Tabelle erscheint, sobald die Auswahl mindestens eine Flasche enthält.
- Betroffen sind die Seiten `/<lang>/sets/<set_id>/` und `/<lang>/stats/` (beide nutzen das Makro `report_grid`). Die Startseite zeigt kein Statistik-Raster und bleibt unverändert.

**Nicht enthalten:**
- Anzeige für andere Länder oder einer länderübergreifenden Tabelle in der Seite. Das ist technisch möglich und durch Tests abgedeckt, aber nicht aktiviert.
- Auswahl der Länder über CLI, `data/` oder `pyproject.toml`.
- Normalisierung über Groß-/Kleinschreibung hinaus (Leerzeichen, Bindestriche, Tippfehler wie `Isaly`).
- Änderungen am Datenmodell, an `data/`, an den JSON-Schemas, an der Validierung (keine Warnung für Schreibvarianten), an der CLI und an `site/builder.py`.

## Akzeptanzkriterien

1. `stats.count_by_region(catalog, set_ids=None, country=None, lang=DEFAULT_LANGUAGE)` liefert eine Liste von `CountEntry`, sortiert wie die übrigen Zählungen (Anzahl absteigend, dann Label ohne Groß-/Kleinschreibung, dann Key).
2. Mit `country` werden nur Flaschen gezählt, deren aufgelöste Brennerei exakt diesen Code hat (`GB-SCT` ≠ `GB`). Flaschen aus anderen Ländern und Flaschen ohne Brennerei-Eintrag fehlen. Mit `country=None` werden alle Flaschen der Auswahl gezählt.
3. Der Key enthält in beiden Fällen das Land: `region:<country>:<region.casefold()>`, z.B. `region:GB-SCT:islay`. Daher sind `GB-SCT`/`Highland` und `US`/`Highland` getrennte Einträge, während `Islay` und `islay` im selben Land ein Eintrag sind.
4. Label, die Region jeweils in der Schreibweise des ersten Vorkommens (Reihenfolge wie `selected_members`):
   - länderspezifisch nur die Region, z.B. `Islay`;
   - länderübergreifend `f"{country_name(country, lang)}, {region}"`, z.B. `Schottland, Islay` (de) / `Scotland, Islay` (en).
   
   `lang` wirkt sich nur auf die länderübergreifenden Labels aus.
5. Fehlende Werte:

   | Fall | länderspezifisch | länderübergreifend |
   | --- | --- | --- |
   | Brennerei ohne `region` | Key `unknown`, Anzeige „unbekannt“ | Key `country:<country>`, Label „<Land>, –“ (z.B. `Schottland, –`) |
   | Flasche ohne Brennerei-Eintrag | wird nicht gezählt | Key `unknown`, Anzeige „unbekannt“ |

   Eine Region, die wörtlich `Unknown` heißt, kollidiert nicht damit (`region:GB-SCT:unknown`). Der Gedankenstrich `–` entspricht der Darstellung einer fehlenden Region auf der Set-Seite.
6. Gibt es keine passende Flasche (z.B. keine schottische Flasche oder eine leere Auswahl), ist das Ergebnis `[]`.
7. Es gibt eine neue Dataclass `RegionStats(country: str | None, entries: list[CountEntry])`. `StatsReport` hat das neue Feld `by_region: list[RegionStats]` mit einem Eintrag pro Land aus `region_countries`, in dieser Reihenfolge und auch dann, wenn `entries` leer ist. `build_report(..., region_countries=None)` nimmt bei `None` den Wert, den `REGION_STATS_COUNTRIES` zum Zeitpunkt des Aufrufs hat, und gibt `lang` an `count_by_region` weiter.
8. `report_grid` zeigt direkt nach „Flaschen pro Land“ für jedes `RegionStats` mit nicht leeren `entries` eine Tabelle.
   - Titel: `t('stats.by_region') ~ ' (' ~ country_name(country) ~ ')'`, falls `country` gesetzt ist, sonst nur `t('stats.by_region')`. Für Schottland ergibt das „Flaschen pro Region (Schottland)“ (de) bzw. „Bottles per region (Scotland)“ (en).
   - Zeilen: länderspezifisch nur die Region, länderübergreifend „Land, Region“.
   - Eine Set-Seite ohne schottische Flasche zeigt keine Regionen-Tabelle.
9. `locales/de.json` und `locales/en.json` bekommen genau einen neuen Schlüssel, `stats.by_region`. Es gibt keinen länderspezifischen Schlüssel, und `test_all_locales_have_same_keys_as_default` bleibt grün.
10. `site/builder.py` bleibt unverändert.
11. `uv run ruff check`, `uv run ruff format --check` und `uv run pytest` sind grün. Alle bestehenden Tests laufen unverändert durch (Ausgangsstand 141, danach 151).
12. Nach der Umsetzung verweist keine Datei im Repository auf diesen Plan; er lässt sich ohne Folgen löschen.

## Relevante Dateien

**Ändern:**
- `src/tastingsets/stats.py` – Konstanten `SCOTLAND` und `REGION_STATS_COUNTRIES`, Dataclass `RegionStats`, Funktion `count_by_region`, Feld `StatsReport.by_region`, `build_report`
- `src/tastingsets/site/templates/_stats_macros.html` – Makro `report_grid`
- `locales/de.json`, `locales/en.json` – Schlüssel `stats.by_region`
- `tests/test_stats.py`, `tests/test_builder.py` – neue Tests; ein bestehender Test bekommt eine zusätzliche Assertion
- `README.md`, `docs/IMPLEMENTATION_PLAN.md` – Dokumentation

**Neu:** keine. Dieser Plan ist temporär und wird anschließend gelöscht.

**Nicht anfassen:**
- `src/tastingsets/models.py`, `src/tastingsets/catalog.py` (`ResolvedMember.country` und `ResolvedMember.region` existieren bereits)
- `src/tastingsets/site/builder.py` (übergibt `build_report(...)` bereits als `report` an beide Seiten)
- `src/tastingsets/i18n.py`, `src/tastingsets/validation.py`, `src/tastingsets/cli.py`, `src/tastingsets/languages.py`
- `src/tastingsets/site/templates/set.html`, `stats.html`, `index.html`, `base.html`, `src/tastingsets/site/static/style.css`
- `data/`, `schemas/`, `tests/conftest.py`, `tests/fixtures/`, `.github/`, `pyproject.toml`
- Dieser Plan selbst: nicht ändern und nicht löschen. Das Löschen übernimmt der Nutzer nach der Abnahme.

## Design

**Wo die Logik liegt:**
- *Zählen* in `stats.py`: Dort liegen alle Zählungen als reine Funktionen auf dem `Catalog`, und `build_report` bündelt sie für die Templates. `count_by_region` folgt dem Muster von `count_by_country` und `count_by_distillery`: `selected_members` plus `_count`, Präfix-Key wie `name:`, `UNKNOWN_KEY` und `lang` mit lokalem Import von `country_name` aus `tastingsets.i18n`, so wie in `count_by_country`.
  - Die Region selbst wird nicht übersetzt (Eigenname). Nur der Ländername im länderübergreifenden Label ist lokalisiert.
  - Das Label entsteht in `stats.py` und nicht im Template, damit Sortierung (nach Label) und Anzeige übereinstimmen und `count_table` unverändert bleibt.
- *Welche Länder* in `stats.py`: Die Konstante `REGION_STATS_COUNTRIES` steht neben `SCOTLAND`. `build_report` liest sie erst beim Aufruf (Standardwert `None` statt der Konstante als Default-Argument). Deshalb bleibt `builder.py` unverändert, Tests können andere Länder per `monkeypatch` aktivieren, und eine spätere Konfiguration kann den Wert über `region_countries` übergeben.
- *Titel und Anzeigebedingung* im Template `_stats_macros.html`: Die Darstellung braucht `t` und `country_name` der jeweiligen Sprache, und beide stehen dort schon im Kontext zur Verfügung. Der Report enthält auch leere `RegionStats`, damit eine spätere Web-App bzw. API sieht, welche Länder konfiguriert sind. Das Template blendet leere Einträge per `for … if region.entries` aus. Eine leere Liste bedeutet genau „keine Flasche aus dem Land in der Auswahl“, denn jede passende Flasche wird gezählt, notfalls unter `unknown`.
- Es entstehen keine neuen Abhängigkeiten zwischen Modulen.

**Titel, zwei Varianten verglichen:**
- **A (gewählt, laut Anforderung):** Ein einziger Schlüssel `stats.by_region`; das Template hängt ` (<Land>)` an. Man braucht nur einen Text pro Sprache, und neue Länder kosten nichts.
- **B:** Ein zweiter Schlüssel mit Platzhalter, z.B. `stats.by_region_in`: „Flaschen pro Region ({country})“. Das wäre flexibler für Sprachen mit anderer Satzstellung, verlangt aber zwei Schlüssel. B wird nicht umgesetzt. Ein späterer Wechsel betrifft nur Template und Locales, nicht `stats.py`.

**Schnittstellen:**
- Öffentliche Python-API: Neu sind `stats.count_by_region`, `stats.SCOTLAND`, `stats.REGION_STATS_COUNTRIES`, `stats.RegionStats` und `StatsReport.by_region`. `build_report` bekommt den optionalen Keyword-Parameter `region_countries`; das ist rückwärtskompatibel. `StatsReport` wird im Repository nur in `build_report` erzeugt. Wer `StatsReport(...)` direkt konstruiert, muss das neue Pflichtfeld angeben (kommt im Repository nicht vor).
- Templates: `report_grid` erwartet `report.by_region`. Die Templates bekommen weiterhin nur View-Daten.
- Locales: ein neuer Schlüssel, rückwärtskompatibel.
- CLI, Datenformat, JSON-Schemas, Konfiguration: unverändert.

## Umsetzungsphasen

### Phase 1 – Statistik-Funktion (`src/tastingsets/stats.py`)

1. Konstanten unter `UNKNOWN_KEY`:
   ```python
   #: ISO 3166-2 code of Scotland.
   SCOTLAND = "GB-SCT"
   #: Countries (exact codes) that get a region table in reports; ``None`` means all countries.
   REGION_STATS_COUNTRIES: tuple[str | None, ...] = (SCOTLAND,)
   ```
   Den Kommentar von `UNKNOWN_KEY` ändern in: „Key used for members whose country or region is not known.“
2. Dataclass direkt nach `CountEntry`:
   ```python
   @dataclass(frozen=True)
   class RegionStats:
       """Bottles per region within one country (exact code) or across all countries (``None``)."""

       country: str | None
       entries: list[CountEntry]
   ```
3. Unter `REGION_STATS_COUNTRIES` eine weitere Konstante:
   ```python
   #: Shown instead of the region in cross-country labels when a distillery has no region.
   MISSING_REGION = "–"
   ```
4. Nach `count_by_country` die Funktion `count_by_region(catalog: Catalog, set_ids: Iterable[str] | None = None, country: str | None = None, lang: str = DEFAULT_LANGUAGE) -> list[CountEntry]` einfügen:
   - Members: `selected_members(catalog, set_ids)`. Bei gesetztem `country` nur die mit `m.country == country` (exakter Code; `m.country` ist `None`, wenn es keinen Brennerei-Eintrag gibt).
   - Gruppierung pro Member, in dieser Reihenfolge:
     1. `m.country is None` (nur länderübergreifend möglich) → `(UNKNOWN_KEY, UNKNOWN_KEY)`.
     2. `m.region is None`: länderspezifisch → `(UNKNOWN_KEY, UNKNOWN_KEY)`; länderübergreifend → `(f"country:{m.country}", f"{country_name(m.country, lang)}, {MISSING_REGION}")`.
     3. Sonst Key `f"region:{m.country}:{m.region.casefold()}"`. Label länderspezifisch `m.region`, länderübergreifend `f"{country_name(m.country, lang)}, {m.region}"`.
   - Die Präfixe folgen dem Muster `name:` aus `count_by_distillery` und vermeiden die Kollision mit `unknown`. Weil das Land im Key steckt, sind gleichnamige Regionen verschiedener Länder getrennt.
   - `country_name` wird wie in `count_by_country` lokal aus `tastingsets.i18n` importiert.
   - Das Ergebnis kommt aus `_count(...)`, das über `labels.setdefault` das Label des ersten Vorkommens behält.
   - Docstring auf Englisch mit diesen Punkten:
     - Flaschen pro Freitext-`region`, Regionen gehören immer zu ihrem Land.
     - `country` schränkt auf einen exakten Ländercode ein (andere Länder und Flaschen ohne Brennerei-Eintrag werden dann nicht gezählt, Label nur die Region); `None` zählt länderübergreifend (Label „<country name>, <region>“, lokalisiert mit `lang`).
     - Vergleich ohne Groß-/Kleinschreibung, Label = erste Schreibweise.
     - Fehlende Region → `unknown` (länderspezifisch) bzw. „<country name>, –“ (länderübergreifend); länderübergreifend zählen Flaschen ohne Brennerei-Eintrag als `unknown`.
     - Leere Liste, wenn keine Flasche passt.
5. `StatsReport`: Feld `by_region: list[RegionStats]` direkt nach `by_country`.
6. `build_report`: neuer letzter Parameter `region_countries: Iterable[str | None] | None = None`. Im Rumpf `countries = REGION_STATS_COUNTRIES if region_countries is None else region_countries` und direkt nach `by_country=...` `by_region=[RegionStats(c, count_by_region(catalog, ids, c, lang)) for c in countries]`. Die Konstante wird bewusst erst beim Aufruf gelesen, nicht als Default-Argument gebunden. Docstring um `region_countries` ergänzen.
7. `tests/test_stats.py` ergänzen. Daten über `make_data_dir` und `DISTILLERIES` aus `conftest` anlegen, so wie in `test_count_by_country_uses_exact_region_code`; das Fixture `catalog` und `as_tuples` wiederverwenden. Standarddaten zur Orientierung: `ardbeg-10` (Brennerei `ardbeg`) 3× (`advent-2025/1`, `advent-2026/2`, `advent-2026/3`), `nonino-grappa` (Brennerei `nonino`) 1× (`advent-2026/1`), `secret-12` (ohne Brennerei-Eintrag) 1× (`advent-2025/2`). Keine Brennerei hat eine `region`.
   - `test_count_by_region_across_countries(catalog)`: `stats.count_by_region(catalog, lang="de")` ergibt `[("country:GB", "Vereinigtes Königreich, –", 3), ("country:IT", "Italien, –", 1), ("unknown", "unknown", 1)]` (Brennereien ohne Region → „Land, –“; die Flasche ohne Brennerei-Eintrag → `unknown`).
   - `test_count_by_region_empty_without_members_from_country(catalog)`: `stats.count_by_region(catalog, country=stats.SCOTLAND) == []` und `stats.count_by_region(catalog, []) == []`.
   - `test_count_by_region_ignores_case(tmp_path)`: `ardbeg` mit `country="GB-SCT", region="Islay"`, `nonino` mit `country="GB-SCT", region="ISLAY"`. Mit `country=stats.SCOTLAND` ergibt das `[("region:GB-SCT:islay", "Islay", 4)]` (`secret-12` fehlt; das Label stammt vom ersten Vorkommen `advent-2025/1`).
   - `test_count_by_region_filters_by_exact_country(tmp_path)`: `ardbeg` `GB-SCT`/`Islay`, `nonino` `IT`/`region="Friuli"`. Erwartet:
     - `country=stats.SCOTLAND` → `[("region:GB-SCT:islay", "Islay", 3)]`
     - dasselbe mit `["advent-2025"]` → `[("region:GB-SCT:islay", "Islay", 1)]`
     - `country="IT"` → `[("region:IT:friuli", "Friuli", 1)]`
     - `country="GB"` → `[]`
     - ohne `country`, `lang="de"` → `[("region:GB-SCT:islay", "Schottland, Islay", 3), ("region:IT:friuli", "Italien, Friuli", 1), ("unknown", "unknown", 1)]`
   - `test_count_by_region_separates_same_region_in_different_countries(tmp_path)`: `ardbeg` `GB-SCT`/`Highland`, `nonino` `US`/`region="highland"`. Erwartet:
     - ohne `country`, `lang="de"` → `[("region:GB-SCT:highland", "Schottland, Highland", 3), ("unknown", "unknown", 1), ("region:US:highland", "Vereinigte Staaten, highland", 1)]` (Gleichstand nach Label sortiert: „unknown“ < „vereinigte …“)
     - mit `lang="en"` liefert `{e.key: e.label for e in ...}` `{"region:GB-SCT:highland": "Scotland, Highland", "region:US:highland": "United States, highland", "unknown": "unknown"}`
   - `test_count_by_region_without_region_is_unknown(tmp_path)`: `ardbeg` `GB-SCT` ohne `region`, `nonino` `GB-SCT` mit `region="Unknown"`. Mit `country=stats.SCOTLAND` ergibt das `[("unknown", "unknown", 3), ("region:GB-SCT:unknown", "Unknown", 1)]`.
   - `test_build_report_region_countries(catalog, monkeypatch)`:
     - `stats.build_report(catalog, region_countries=[None, "IT"]).by_region == [stats.RegionStats(None, [stats.CountEntry("country:GB", "Vereinigtes Königreich, –", 3), stats.CountEntry("country:IT", "Italien, –", 1), stats.CountEntry("unknown", "unknown", 1)]), stats.RegionStats("IT", [stats.CountEntry("unknown", "unknown", 1)])]` (Standardsprache `de`)
     - mit `lang="en"` beginnt `by_region[0].entries[0].label` mit „United Kingdom, “ (Beleg, dass `lang` weitergereicht wird)
     - nach `monkeypatch.setattr(stats, "REGION_STATS_COUNTRIES", ("IT",))` ergibt `stats.build_report(catalog).by_region` `[stats.RegionStats("IT", [stats.CountEntry("unknown", "unknown", 1)])]`
   - Den bestehenden `test_build_report_bundles_all_statistics` um `assert report.by_region == [stats.RegionStats(stats.SCOTLAND, [])]` ergänzen, sonst nichts ändern.

**Checks:** `uv run pytest tests/test_stats.py tests/test_groups.py`, `uv run ruff check`, `uv run ruff format --check`.

### Phase 2 – Locales und Template

*Hängt an Phase 1.*

8. `locales/de.json`: nach `"stats.by_country"` den Schlüssel `"stats.by_region": "Flaschen pro Region"` einfügen.
9. `locales/en.json`: an derselben Stelle `"stats.by_region": "Bottles per region"`.
10. `src/tastingsets/site/templates/_stats_macros.html`, Makro `report_grid`: direkt nach der Zeile mit `count_table(t('stats.by_country'), report.by_country)` einfügen:
   ```jinja
   {% for region in report.by_region if region.entries %}
   {% set title = t('stats.by_region') ~ (' (' ~ country_name(region.country) ~ ')' if region.country else '') %}
   {{ count_table(title, region.entries) }}
   {% endfor %}
   ```
   - `count_table` bleibt unverändert. Einträge mit `key == 'unknown'` zeigt es bereits als `stats.unknown` an, alle anderen mit `entry.label`. Die Beschriftung der Zeilen (nur Region bzw. „Land, Region“) kommt also fertig aus `stats.py`.
   - `country_name` steht über `with context` zur Verfügung (wie `t`) und liefert den lokalisierten Namen, z.B. „Schottland“ bzw. „Scotland“ für `GB-SCT`.
   - Der Titel ist ein normaler `str` und wird beim Rendern escaped.
   - In `locales/*.json` gibt es keinen länderspezifischen Schlüssel.
11. `tests/test_builder.py` ergänzen. Daten über `make_data_dir`, `DISTILLERIES` und `TASTING_SETS` aus `conftest`, importiert im Test wie in `test_set_page_shows_region_name_and_free_text_region`.
    - `test_scotland_region_stats_only_for_sets_with_scottish_members(tmp_path)`:
      - Daten: `ardbeg` `GB-SCT`/`Islay`, `nonino` unverändert (`IT`); `tasting_sets=[*TASTING_SETS, {"_id": "grappa-2026", "names": {"de": "Grappa 2026"}, "members": [{"member_id": "1", "spirit_id": "nonino-grappa"}]}]`; Build mit `languages=["de", "en"]`.
      - `de/sets/advent-2025/index.html` und `de/stats/index.html` enthalten „Flaschen pro Region (Schottland)“; `de/stats/index.html` enthält `<td>Islay</td>` (nur die Region, ohne Land; auf der Set-Seite steht `<td>Islay</td>` schon in der Member-Tabelle und taugt dort nicht als Beleg); in beiden gilt `html.index("Flaschen pro Land") < html.index("Flaschen pro Region (Schottland)")`.
      - `en/stats/index.html` enthält „Bottles per region (Scotland)“.
      - `de/sets/grappa-2026/index.html` enthält „Flaschen pro Land“, aber nicht „Flaschen pro Region“.
    - `test_region_stats_hidden_without_members_from_country(data_dir, tmp_path)`: Standarddaten; weder `de/stats/index.html` noch `de/sets/advent-2025/index.html` enthält „Flaschen pro Region“.
    - `test_region_stats_title_and_labels_for_countries_and_across(tmp_path, monkeypatch)`: Der Test belegt, dass weitere Länder bzw. eine länderübergreifende Tabelle ohne neue Locale-Schlüssel funktionieren, mit den richtigen Zeilenbeschriftungen.
      - Daten: `ardbeg` `GB-SCT`/`Islay`, `nonino` `IT`/`region="Friuli"`.
      - `monkeypatch.setattr(stats, "REGION_STATS_COUNTRIES", (None, stats.SCOTLAND, "IT"))` (Import `from tastingsets import stats`); Build mit `languages=["de"]`.
      - `de/stats/index.html` enthält `<h3>Flaschen pro Region</h3>`, „Flaschen pro Region (Schottland)“ und „Flaschen pro Region (Italien)“.
      - Zeilen der länderübergreifenden Tabelle: `<td>Schottland, Islay</td>` und `<td>Italien, Friuli</td>`.
      - Zeilen der länderspezifischen Tabellen: `<td>Islay</td>` und `<td>Friuli</td>`.
      - Die Positionen (`html.index`) sind aufsteigend in der Reihenfolge „Flaschen pro Land“, `<h3>Flaschen pro Region</h3>`, `<td>Schottland, Islay</td>`, „Flaschen pro Region (Schottland)“, `<td>Islay</td>`, „Flaschen pro Region (Italien)“, `<td>Friuli</td>`.

**Checks:** `uv run pytest` (komplett, inklusive `test_i18n.py::test_all_locales_have_same_keys_as_default` und `test_languages.py`), `uv run ruff check`, `uv run ruff format --check`.

### Phase 3 – Dokumentation

*Hängt an Phase 2.*

12. `README.md` und `docs/IMPLEMENTATION_PLAN.md` wie unter „Auswirkung auf die Dokumentation“ beschrieben anpassen. Alle dauerhaften Entscheidungen, Annahmen und Grenzen aus diesem Plan landen dort, ohne Verweis auf diesen Plan.

**Checks:** `uv run tastingsets validate` (0 Fehler), Verifikationsschritt 8, Durchsicht der geänderten Abschnitte.

## Verifikation

1. `uv run ruff check` → keine Befunde.
2. `uv run ruff format --check` → alle Dateien bereits formatiert.
3. `uv run pytest` → alle Tests grün: 141 bisherige plus 10 neue (7 in `test_stats.py`, 3 in `test_builder.py`) = 151 Tests.
4. `uv run tastingsets validate` → Exit-Code 0, keine Fehler (Warnungen je nach Datenstand möglich).
5. `uv run tastingsets build --out dist` → Exit-Code 0.
6. `grep -c "Flaschen pro Region (Schottland)" dist/de/sets/advent-2026/index.html dist/de/stats/index.html` → je `1`; `grep -c "Bottles per region (Scotland)" dist/en/stats/index.html` → `1`.
7. Manuell: `python -m http.server -d dist` starten und `http://localhost:8000/de/sets/advent-2026/` öffnen. Die Karte „Flaschen pro Region (Schottland)“ steht nach „Flaschen pro Land“ und zeigt mit dem aktuellen Datenstand Highland 3, Islay 3, Speyside 3, Lowland 2, Campbeltown 1. Danach den Server beenden und `dist/` löschen (`rm -rf dist`), weil `dist/` nur ein Build-Ergebnis ist.
8. `grep -rn "PLAN_SCOTLAND_REGION_STATS" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=dist --exclude=PLAN_SCOTLAND_REGION_STATS.md .` → keine Treffer (Exit-Code 1). Damit lässt sich der Plan ohne Folgen löschen.

## Annahmen, Risiken und offene Punkte

- **Annahme:** Der in der Anforderung genannte Code „GBT-SCT“ ist ein Tippfehler; gemeint ist der ISO-3166-2-Code `GB-SCT`, den `data/distilleries/scotland.json` verwendet.
- **Annahme:** „Aus Schottland“ heißt: aufgelöste Brennerei mit exakt `country == "GB-SCT"`. Brennereien mit `GB` (ohne Region) oder Flaschen ohne Brennerei-Eintrag zählen nicht, auch wenn die Kategorie „Scotch“ heißt.
- **Annahme:** Bei Schreibvarianten zeigt die Tabelle die Schreibweise des ersten Vorkommens (Reihenfolge der Sets im Catalog, dann der Members). Das ist deterministisch und entspricht dem Verhalten von `_count`.
- **Annahme:** Das Format „<Text> (<Land>)“ mit runden Klammern passt für alle Sprachen. Braucht eine Sprache eine andere Satzstellung, wechselt man auf Variante B (siehe „Design“).
- **Risiko:** Leerzeichen oder Tippfehler in `region` (`"Islay "`, `"Isaly"`) ergeben weiterhin getrennte Einträge. Das liegt bewusst außerhalb des Umfangs.
- **Annahme:** Länderübergreifend wird eine Brennerei mit bekanntem Land, aber ohne `region` als „<Land>, –“ angezeigt (Key `country:<code>`), statt mit „unbekannt“ als Region. So bleibt das Format „Land, Region“ erhalten, `stats.py` braucht keine UI-Texte, und `–` entspricht der Set-Seite. Mit „unbekannt“ wäre ein zusätzliches Feld in `CountEntry` oder Logik im Template nötig.
- **Annahme:** Das Trennzeichen „, “ zwischen Land und Region ist für alle Sprachen fest und nicht übersetzt.
- **Annahme:** Die Keys enthalten den Ländercode auch länderspezifisch (`region:GB-SCT:islay`). Ein einheitliches Format für beide Fälle; die Anzeige ist davon nicht betroffen.
- **Risiko:** Länderübergreifend wird nach dem Label sortiert, das mit dem lokalisierten Ländernamen beginnt. Bei gleicher Anzahl stehen die Einträge eines Landes daher zusammen; die Reihenfolge hängt von der Sprache ab.
- **Risiko:** Das neue Pflichtfeld in `StatsReport` bricht Code, der `StatsReport` direkt konstruiert. Im Repository geschieht das nur in `build_report`.
- **Offen:** keine.

## Auswirkung auf die Dokumentation

Dieser Plan wird nach der Umsetzung gelöscht. Die folgenden Texte müssen deshalb für sich allein verständlich sein und dürfen nicht auf diesen Plan verweisen.

**`README.md`:**
- Abschnitt „Data model“, Tabellenzeile `data/distilleries/`: Die Beschreibung von `region` ergänzen um „used for the region statistics, compared case-insensitively“.
- Abschnitt „Architecture and outlook“: Den Absatz „**Region statistics (planned, not implemented yet).**“ samt Aufzählung ersetzen durch einen Absatz „**Region statistics.**“ mit diesen Punkten (auf Englisch):
  - *Code:* `count_by_region(catalog, set_ids, country=None, lang)` in `src/tastingsets/stats.py` zählt die Flaschen nach `region`, ohne Groß-/Kleinschreibung (Label = erste Schreibweise). Eine Region gehört immer zu ihrem Land (`GB-SCT`/`Highland` ≠ `US`/`Highland`).
    - Mit `country` (exakter Code, `GB-SCT` ≠ `GB`) werden nur Flaschen dieses Landes gezählt, Flaschen ohne Brennerei-Eintrag fehlen. Das Label ist nur die Region; fehlt sie, erscheint `unknown`.
    - Mit `None` wird länderübergreifend gezählt. Das Label ist „<localized country name>, <region>“, z.B. „Scotland, Islay“. Fehlt die Region, steht „<country>, –“ da; Flaschen ohne Brennerei-Eintrag zählen als `unknown`.
  - *Report:* `StatsReport.by_region` ist eine Liste von `RegionStats(country, entries)`, einer pro Eintrag von `REGION_STATS_COUNTRIES` (heute `(SCOTLAND,)` mit `SCOTLAND = "GB-SCT"`; `None` = länderübergreifend).
  - *Site:* Nach „Bottles per country“ steht pro nicht leerem Eintrag eine Tabelle. Der Titel kommt aus dem einen Schlüssel `stats.by_region`, ergänzt um ` (<localized country name>)`, z.B. „Bottles per region (Scotland)“, länderübergreifend ohne Zusatz. Eine Tabelle erscheint nur, wenn die Auswahl mindestens eine Flasche aus dem Land enthält.
  - *Weitere Länder:* Den Code zu `REGION_STATS_COUNTRIES` hinzufügen; Locales und Templates bleiben unverändert.

**`docs/IMPLEMENTATION_PLAN.md`:**
- Phase 2, Punkt 5 (`region`): „keine Auswirkung auf die Statistik“ ersetzen durch „wird für die Regionen-Statistik genutzt (siehe Phase 5a)“.
- Phase 5, Punkt 14: Nach `count_by_country` den Eintrag `count_by_region` ergänzen: „Flaschen pro `region` innerhalb ihres Landes, optional auf ein Land eingeschränkt (exakter Code, Label nur die Region), sonst länderübergreifend (Label „Land, Region“); ohne Groß-/Kleinschreibung.“
- Nach Phase 5 einen neuen, in sich vollständigen Abschnitt „### Phase 5a – Regionen-Statistik (nachträglich ergänzt)“ anlegen. Ohne Verweis auf diesen Plan, mit diesen Punkten:
  - `count_by_region`:
    - Filter: exaktes Land oder länderübergreifend.
    - Keys: `region:<country>:<casefold>`, `country:<country>` (länderübergreifend ohne Region) und `unknown`.
    - Labels: länderspezifisch die Region, länderübergreifend „<Land>, <Region>“ bzw. „<Land>, –“, jeweils die erste Schreibweise.
    - `lang` für den Ländernamen.
  - `RegionStats`, `StatsReport.by_region`, `REGION_STATS_COUNTRIES = (SCOTLAND,)`, `build_report(..., region_countries=None)` (liest die Konstante beim Aufruf).
  - Template: eine Tabelle pro nicht leerem Eintrag nach „Flaschen pro Land“, Titel aus `stats.by_region` plus „ (<Land>)“ über `country_name`.
  - Tests in `tests/test_stats.py` und `tests/test_builder.py`.
- Abschnitt „Decisions“: Einen neuen Punkt anfügen: „Regionen-Statistik generisch (Land oder länderübergreifend), in der Seite vorerst nur für Schottland (`GB-SCT`). Regionen werden ohne Groß-/Kleinschreibung verglichen und gehören immer zu ihrem Land; länderübergreifend lautet die Zeile „Land, Region“, länderspezifisch nur „Region“. Der Titel kommt aus einem einzigen Locale-Schlüssel, das Land wird dynamisch ergänzt. Eine Tabelle erscheint nur, wenn die Auswahl mindestens eine Flasche aus dem Land enthält. Weitere Länder über `REGION_STATS_COUNTRIES`.“ Unter „**Nicht enthalten:**“ ergänzen: „Anzeige der Regionen-Statistik für weitere Länder oder länderübergreifend, Normalisierung von Regionsnamen über Groß-/Kleinschreibung hinaus“.
- Abschnitt „Further Considerations“: einen neuen, fortlaufend nummerierten Punkt anfügen: „**Regionen-Statistik erweitern:** Soll länderübergreifend statt „Land, –“ „Land, unbekannt“ erscheinen, braucht `CountEntry` (oder ein eigener Eintragstyp) Land und Region getrennt, damit das Template übersetzen kann. Braucht eine Sprache eine andere Satzstellung als „Text (Land)“, einen zweiten Locale-Schlüssel mit Platzhalter `{country}` einführen.“
