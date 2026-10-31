# Umsetzungsplan: TastingSets – Architektur für statische Seite, offen für Web-App und MongoDB

> Dieses Dokument ist die verbindliche Vorgabe für die Umsetzung. Die Phasen bauen aufeinander auf.
> Code, Bezeichner, Feldnamen und Kommentare sind auf Englisch, die Oberfläche der Webseite auf Deutsch (i18n vorbereitet).

## Kontext und Anforderungen

**Ziel:** Der Inhalt von Tasting Sets (z.B. Adventskalender mit Whisky-Samples) soll als Webseite veröffentlicht werden.

- **Jetzt:** Eine statische HTML-Seite auf GitHub Pages. Die Daten liegen als JSON-Dateien im Repository.
- **Später:** Eine dynamische Web-App mit MongoDB als Datenquelle.
- Die JSON-Dateien im Repository müssen genauso aufgebaut sein wie die späteren MongoDB-Dokumente.
- Fehler in den Daten werden mit Pydantic erkannt.
- Elemente desselben Typs dürfen auf mehrere Dateien verteilt sein.
- Innerhalb eines Tasting Sets sind die IDs der Set Member eindeutig, über mehrere Sets hinweg meist nicht.
- Ein Schnaps darf eine Brennerei namentlich nennen, auch wenn es zu ihr keinen Eintrag in der Brennerei-Liste gibt.

**Features aus Nutzersicht:**
- Übersicht über ein bestimmtes Tasting Set: welche Nummer (Flasche) welchen Inhalt hat, mit allen Zusatzinformationen.
- Übersicht über alle Tasting Sets: welche Brennerei wie oft, welche Art Schnaps wie oft, welche Schnäpse mehrfach vorkommen usw.

**Features aus Entwicklersicht:**
- Jede Funktion hat mindestens einen einfachen Unit-Test.
- Ein Push auf `main` aktualisiert die GitHub Page.
- Ein Push auf einen Feature-Branch startet einen Check, der Schnäpse meldet, deren Brennerei keinen Eintrag in der Brennerei-Liste hat. Das ist eine Warnung, kein Fehler.

## Architektur-Überblick

Python-Paket `tastingsets` mit klar getrennten Schichten:

```
models  →  repository (JSON jetzt, Mongo später)  →  catalog (Auflösung der Referenzen)
                                                        ├→ validation
                                                        ├→ stats
                                                        └→ site builder (Jinja2)  ← i18n
cli: validate | build | schema
```

- Jeder Ordner unter `data/` entspricht einer späteren MongoDB-Collection.
- Jedes Dokument hat ein `_id`-Feld mit einem gut lesbaren Kurznamen (Slug), z.B. `ardbeg`.
- Set Member sind kein eigenes Dokument, sondern stecken direkt im Tasting-Set-Dokument.
- Für die spätere Web-App kommen nur ein `MongoRepository` und eine FastAPI-App dazu, die den Seitengenerator ersetzt. Modelle, Validierung, Statistik und Templates bleiben unverändert.

### Beispiel-Datenformat

`data/categories/categories.json`
```json
[
  { "_id": "single-malt-scotch", "names": { "de": "Single Malt Scotch Whisky", "en": "Single Malt Scotch Whisky" } },
  { "_id": "grappa", "names": { "de": "Grappa", "en": "Grappa" } }
]
```

`data/distilleries/scotland.json`
```json
[
  { "_id": "ardbeg", "name": "Ardbeg", "country": "GB" }
]
```

`data/spirits/a-m.json`
```json
[
  {
    "_id": "ardbeg-10",
    "name": "Ardbeg 10 Years",
    "category_id": "single-malt-scotch",
    "distillery_id": "ardbeg",
    "abv": 46.0,
    "url": "https://www.whiskybase.com/whiskies/whisky/1234"
  },
  {
    "_id": "secret-speyside-12",
    "name": "Secret Speyside 12 Years",
    "category_id": "single-malt-scotch",
    "distillery_name": "Unbekannte Speyside-Brennerei",
    "abv": 48.2
  }
]
```

`data/tasting_sets/advent-2026.json` (eine Datei darf ein einzelnes Objekt oder eine Liste enthalten)
```json
{
  "_id": "advent-2026",
  "name": "Adventskalender 2026",
  "year": 2026,
  "members": [
    { "member_id": "1", "spirit_id": "ardbeg-10" },
    { "member_id": "2", "spirit_id": "secret-speyside-12", "notes": "Fassstärke" }
  ]
}
```

## Steps

### Phase 1 – Projektgerüst

1. `pyproject.toml` anlegen:
   - uv, Python 3.12 oder neuer, src-Layout.
   - Abhängigkeiten: `pydantic>=2`, `jinja2`, `babel`.
   - Entwicklungs-Abhängigkeiten: `pytest`, `ruff`.
   - Einstiegspunkt: `tastingsets = tastingsets.cli:main`.
   - Konfiguration für ruff und pytest (`testpaths = ["tests"]`).
   - Dazu eine `.gitignore` mit mindestens `dist/`, `.venv/`, `__pycache__/` und `.pytest_cache/`.
2. Ordnerstruktur:
   ```
   data/
     categories/        z.B. categories.json
     distilleries/      z.B. scotland.json, italy.json
     spirits/           z.B. a-m.json, n-z.json
     tasting_sets/      eine Datei pro Set, z.B. advent-2025.json
   locales/
     de.json
     en.json            Texte der Oberfläche
   src/tastingsets/
     __init__.py
     __main__.py
     models.py
     repository/
       __init__.py
       base.py
       json_repository.py
     catalog.py
     validation.py
     stats.py
     i18n.py
     cli.py
     site/
       __init__.py
       builder.py
       templates/
       static/
   tests/
     fixtures/data/     kleiner, gezielt gebauter Datensatz, auch mit absichtlich fehlerhaften Fällen
   schemas/             generierte JSON-Schemas
   .github/workflows/
   ```

### Phase 2 – Datenmodell (`models.py`)

*Hängt an Phase 1.*

3. Basisklasse `Document(BaseModel)`:
   - `id: str` mit Alias `_id`, geprüft per Regex `^[a-z0-9]+(-[a-z0-9]+)*$`.
   - `model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)`. Durch `extra="forbid"` fallen Tippfehler in Feldnamen auf.
   - `model_dump(by_alias=True)` liefert direkt ein Mongo-Dokument.
4. `Category(Document)`:
   - `names: dict[str, str]` mit dem Sprachcode als Schlüssel.
   - Ein Validator verlangt, dass mindestens `de` vorhanden ist.
5. `Distillery(Document)`:
   - `name: str`, optional `display_name: str | None`.
   - `country: str` als ISO-3166-Alpha-2-Code in Großbuchstaben, gegen die Babel-Länderliste geprüft.
6. `Spirit(Document)`:
   - Pflicht: `name: str`, `category_id: str`, `abv: float` (größer 0, höchstens 100).
   - Optional: `display_name`, `distillery_id`, `distillery_name`, `url: HttpUrl`.
   - Ein `model_validator` prüft, dass `distillery_id` oder `distillery_name` gesetzt ist.
7. `SetMember(BaseModel)`:
   - Kein eigenes Dokument, sondern Teil des Tasting Sets. Gleiche Konfiguration wie oben, aber ohne `_id`.
   - `member_id: str` mit Regex `^[A-Za-z0-9_-]+$`.
   - `spirit_id: str`, optional `notes: str | None`.
8. `TastingSet(Document)`:
   - `name: str`, optional `display_name` und `year: int | None`, `members: list[SetMember]`.
   - Ein Validator stellt sicher, dass `member_id` innerhalb des Sets eindeutig ist.
   - Die Methode `fqn(member) -> str` liefert den vollständigen Namen `"<set_id>/<member_id>"`, z.B. `advent-2026/24`. Damit ist jeder Set Member über alle Sets hinweg eindeutig.
   - Die Reihenfolge der Members entspricht der Reihenfolge in der Datei.
   - Hilfseigenschaft `label`: `display_name`, falls gesetzt, sonst `name`. Dasselbe für `Distillery` und `Spirit`.

### Phase 3 – Datenzugriff

*Hängt an Phase 2.*

9. `repository/base.py`:
   - Protocol `Repository` mit `categories()`, `distilleries()`, `spirits()`, `tasting_sets()`, jeweils als Liste.
   - Dazu `source_of(collection, id) -> str | None`, das die Quelldatei liefert (für Fehlermeldungen).
   - Konstante `COLLECTIONS: dict[str, type[Document]]`, die die Ordnernamen `categories`, `distilleries`, `spirits` und `tasting_sets` den Modellklassen zuordnet.
10. `JsonRepository(data_dir: Path)`:
    - Lädt pro Collection alle `*.json` in sortierter Reihenfolge.
    - Eine Datei darf ein einzelnes Objekt oder eine Liste von Objekten enthalten.
    - Pydantic-Fehler werden mit Dateiname und Index gesammelt, nicht beim ersten Fehler abgebrochen. Sie stehen über eine Eigenschaft `load_errors` zur Verfügung.
    - Eine doppelte `_id` innerhalb einer Collection ist ein Fehler, auch wenn die beiden Einträge in verschiedenen Dateien stehen.
11. `catalog.py`:
    - `Catalog` (Dataclass) mit Dictionaries nach ID, gebaut aus einem Repository über `Catalog.from_repository(repo)`.
    - Auflösungs-Funktionen, die `ResolvedMember` liefern. Felder:
      - `fqn`, `member_id`, `notes`
      - `spirit`, `category`
      - `distillery: Distillery | None`
      - `distillery_label`: Anzeigename der Brennerei, sonst Rückfall auf `distillery_name`
    - Funktionen: `resolve_set(set_id) -> list[ResolvedMember]` und `resolve_member(fqn) -> ResolvedMember`.
    - Diese Schicht ist später direkt von FastAPI nutzbar.

### Phase 4 – Validierung

*Hängt an Phase 3.*

12. `validation.py`: `validate(repo) -> list[Issue]`.
    - `Issue` (Dataclass) mit `severity: Severity` (`ERROR` oder `WARNING`), `code: str`, `message: str`, `file: str | None` und `object_id: str | None`.
    - **ERROR**, mit folgenden Codes:
      - `SCHEMA`: Pydantic-Fehler
      - `DUPLICATE_ID`: doppelte `_id`
      - `UNKNOWN_SPIRIT`: `spirit_id` zeigt auf keinen Schnaps
      - `UNKNOWN_CATEGORY`: `category_id` zeigt auf keine Kategorie
      - `UNKNOWN_DISTILLERY`: `distillery_id` zeigt auf keine Brennerei. Das ist fast sicher ein Tippfehler; der erlaubte Fall „Brennerei hat keinen Eintrag“ wird ausdrücklich über `distillery_name` abgebildet.
      - `DUPLICATE_MEMBER_ID`: doppelte `member_id` innerhalb eines Sets
    - **WARNING**, mit folgenden Codes:
      - `MISSING_DISTILLERY_ENTRY`: nur `distillery_name` gesetzt, ohne `distillery_id`.
      - `DISTILLERY_NAME_MATCHES_ENTRY`: `distillery_name` entspricht dem Namen einer bereits existierenden Brennerei (Groß-/Kleinschreibung egal); Hinweis, besser `distillery_id` zu verwenden.
      - Optional `UNUSED_SPIRIT`: der Schnaps kommt in keinem Set vor.
13. CLI `tastingsets validate [--data DIR] [--strict]`:
    - Gibt die Issues lesbar aus.
    - Ist die Umgebungsvariable `GITHUB_ACTIONS=true` gesetzt, zusätzlich als GitHub-Annotation: `::warning file=<file>,title=<code>::<message>` bzw. `::error ...`.
    - Exit-Code 1 nur bei Fehlern; mit `--strict` auch bei Warnungen. Sonst 0.

### Phase 5 – Statistik (`stats.py`)

*Hängt an Phase 3, kann parallel zu Phase 4 laufen.*

14. Reine Funktionen mit der Signatur `(catalog: Catalog, set_ids: list[str] | None = None)`. `None` heißt: alle Sets.
    - `count_by_distillery`: zählt bei fehlendem Eintrag nach `distillery_name`.
    - `count_by_category`
    - `count_by_country`: Schnäpse ohne Brennerei-Eintrag zählen als „unbekannt“.
    - `repeated_spirits`: Schnäpse, die mehr als einmal vorkommen, jeweils mit der Liste der FQNs, innerhalb eines Sets und über mehrere Sets hinweg.
    - `abv_summary`: Minimum, Maximum, Durchschnitt.
    - Rückgabe als kleine Dataclasses, z.B. `CountEntry(key, label, count)`, sortiert nach Anzahl absteigend und bei Gleichstand nach Label.

### Phase 6 – i18n und Seitengenerator

*Hängt an Phase 4 und 5.*

15. `i18n.py`:
    - Lädt `locales/<lang>.json` (flache Key-Value-Paare) und stellt `t(key)` bereit. Fehlt ein Key, wird auf `de` zurückgefallen, danach auf den Key selbst.
    - `localized(names, lang)` für Kategorienamen.
    - `country_name(code, lang)` über `babel.Locale(lang).territories`.
    - Die Sprachen kommen aus einer Konfiguration (Konstante bzw. CLI-Option), in v1 nur `["de"]`.
16. `site/builder.py`:
    - `build(repo, out_dir, base_url="/", languages=["de"])`. Zuerst läuft die Validierung; bei Fehlern wird mit einer Exception abgebrochen.
    - Jinja2-Environment mit `autoescape=True` und den Funktionen `t`, `localized`, `country_name` und `url_for(path)`; `url_for` beachtet `base_url`.
    - Ergebnis für jede Sprache:
      - `/<lang>/index.html`: Liste der Sets und kurze Gesamtstatistik
      - `/<lang>/sets/<set_id>/index.html`: Tabelle mit Nummer, Schnaps, Art, Brennerei, Land, Alkoholgehalt, Link; dazu die Statistik dieses Sets
      - `/<lang>/stats/index.html`: ausführliche Gesamtstatistik
    - `/index.html` leitet auf die Standardsprache weiter (Meta-Refresh).
    - `static/` (CSS) wird nach `out_dir/static/` kopiert.
17. Templates: `base.html`, `index.html`, `set.html`, `stats.html` und `_stats_macros.html`.
    - Die Templates bekommen nur aufgelöste View-Daten (`ResolvedMember`, Statistik-Dataclasses) und keine Repository-Objekte. So kann FastAPI sie später unverändert nutzen.
    - Schlichtes, modernes CSS ohne externe Abhängigkeiten.
18. CLI:
    - `tastingsets build [--data DIR] [--out dist] [--base-url /TastingSets/]`
    - `tastingsets schema [--out schemas]`: schreibt pro Collection `schemas/<collection>.schema.json`. Das Schema beschreibt ein Array des jeweiligen Modells oder ein einzelnes Objekt, also `oneOf`.
    - Zusätzlich ordnet `.vscode/settings.json` über `json.schemas` die Ordner in `data/` diesen Schemas zu, z.B. `data/spirits/*.json` → `schemas/spirits.schema.json`. So gibt es Autovervollständigung und Live-Validierung im Editor.

### Phase 7 – Tests

*Läuft parallel zu jeder Phase.*

19. Pro Modul eine Testdatei, mindestens ein Test pro öffentlicher Funktion:
    - `test_models.py`: gültige und ungültige Werte für Slug, Alkoholgehalt, URL, Ländercode, die beiden Brennerei-Felder und eindeutige `member_id`; außerdem `fqn`
    - `test_json_repository.py`: einzelnes Objekt oder Liste, mehrere Dateien, doppelte ID über Dateien hinweg, Schemafehler mit Dateiname (mit `tmp_path`)
    - `test_catalog.py`: Auflösung mit und ohne Brennerei-Eintrag, `resolve_member` über FQN
    - `test_validation.py`: jeder Issue-Code mindestens einmal
    - `test_stats.py`: jede Statistik-Funktion, für alle Sets und für ausgewählte Sets
    - `test_i18n.py`: `t` mit Rückfall, `localized`, `country_name`
    - `test_builder.py`: Build in `tmp_path`, die erwarteten Dateien existieren, Namen und Nummern stehen im HTML, `base_url` wird in den Links beachtet, Abbruch bei Fehlern
    - `test_cli.py`: Exit-Codes von `validate` (normal und `--strict`), Format der GitHub-Annotationen (mit `monkeypatch` auf `GITHUB_ACTIONS`)
    - `test_real_data.py`: das echte `data/` hat keine Fehler
    - `test_schemas_up_to_date.py`: die eingecheckten Schemas entsprechen den aktuellen Modellen

### Phase 8 – CI/CD

*Hängt an Phase 4 und 6.*

20. `.github/workflows/ci.yml`:
    - Läuft bei `push` auf alle Branches außer `main` (`branches-ignore: [main]`) und bei `pull_request`.
    - Schritte:
      1. `actions/checkout`
      2. `astral-sh/setup-uv`
      3. `uv sync`
      4. `uv run ruff check`
      5. `uv run ruff format --check`
      6. `uv run pytest`
      7. `uv run tastingsets validate`: Warnungen erscheinen als Annotation, der Job bleibt grün.
      8. `uv run tastingsets build --out dist` als Probe-Build.
21. `.github/workflows/pages.yml`:
    - Läuft bei `push` auf `main` und lässt sich zusätzlich von Hand starten (`workflow_dispatch`).
    - Berechtigungen: `contents: read`, `pages: write`, `id-token: write`.
    - Gleichzeitig laufende Deploys werden über `concurrency: { group: pages, cancel-in-progress: false }` verhindert.
    - Job `build`: Tests, Validierung (Fehler brechen ab), `uv run tastingsets build --out dist --base-url /TastingSets/`, dann `actions/upload-pages-artifact` mit `path: dist`.
    - Job `deploy`: hängt von `build` ab, Umgebung `github-pages`, ruft `actions/deploy-pages` auf.
22. Einmalig von Hand: In den Repo-Einstellungen unter Settings → Pages die Quelle (Source) auf „GitHub Actions“ stellen. In der README dokumentieren.

### Phase 9 – Doku und Startdaten

23. README ergänzen:
    - Datenmodell
    - Ordner-Konventionen
    - CLI-Befehle (`uv run tastingsets validate | build | schema`)
    - Wie man ein neues Set oder einen neuen Schnaps hinzufügt
    - Lokale Vorschau mit `python -m http.server -d dist`
    - Ausblick auf MongoDB
24. Kleine echte Startdaten in `data/` anlegen:
    - 2–3 Kategorien
    - 2 Brennereien
    - 4 Schnäpse, davon einer nur mit `distillery_name`
    - 1 Tasting Set

## Relevant files

Alle Dateien sind neu.

- `pyproject.toml` – Abhängigkeiten, Einstiegspunkt, Konfiguration für ruff und pytest
- `src/tastingsets/models.py` – `Document`, `Category`, `Distillery`, `Spirit`, `SetMember`, `TastingSet`
- `src/tastingsets/repository/base.py` – Protocol `Repository`, `COLLECTIONS`
- `src/tastingsets/repository/json_repository.py` – `JsonRepository`
- `src/tastingsets/catalog.py` – `Catalog`, `ResolvedMember`
- `src/tastingsets/validation.py` – `Issue`, `Severity`, `validate`
- `src/tastingsets/stats.py` – Statistik-Funktionen
- `src/tastingsets/i18n.py` – `t`, `localized`, `country_name`
- `src/tastingsets/site/builder.py` und `src/tastingsets/site/templates/*.html`
- `src/tastingsets/cli.py` – Unterbefehle `validate`, `build`, `schema`
- `.github/workflows/ci.yml`, `.github/workflows/pages.yml`
- `.vscode/settings.json` – Schema-Zuordnung für den Editor

## Verification

1. `uv run pytest` ist grün und `uv run ruff check` ohne Befunde.
2. Validierung:
   - `uv run tastingsets validate --data tests/fixtures/data` liefert genau die erwarteten Issue-Codes.
   - Gegen `data/` gibt es keine Fehler und genau eine Warnung `MISSING_DISTILLERY_ENTRY`.
3. `uv run tastingsets build --out dist`, dann `python -m http.server -d dist` starten und von Hand ansehen: Set-Seite, Gesamtstatistik, Links mit `base_url`.
4. Feature-Branch:
   - Einen Schnaps nur mit `distillery_name` pushen: die Warnung erscheint als Annotation, der Job ist grün.
   - Eine kaputte `spirit_id` pushen: der Job ist rot.
5. Nach dem Merge auf `main` ist die Seite unter `https://<user>.github.io/TastingSets/` aktualisiert.
6. Im Editor in `data/spirits/*.json` ein unbekanntes Feld eintragen: die Schema-Warnung wird angezeigt.

## Decisions

- Ein Ordner pro Collection. Die Dateinamen darin sind frei wählbar, es werden alle `*.json` geladen.
- Lesbare Slugs als `_id`, keine UUIDs.
- Set Member stecken im Tasting Set. Innerhalb eines Sets sind sie durch das Modell eindeutig, über alle Sets hinweg durch den FQN `<set_id>/<member_id>`.
- Brennerei-Referenz über zwei Felder: `distillery_id` und `distillery_name` als Rückfall.
  - Eine `distillery_id` ohne passenden Eintrag ist ein Fehler.
  - Nur `distillery_name` ohne `distillery_id` ist eine Warnung.
- Kategorien (Art des Schnapses) sind eine eigene Collection mit lokalisierten Namen.
- Die Statistik wird vorab gerendert, pro Set und gesamt. Eine freie Auswahl von Sets kommt erst mit der dynamischen App.
- Mehrsprachigkeit ist technisch vorbereitet, gebaut wird in v1 nur Deutsch.
- Tooling: uv, `pyproject.toml`, pytest, ruff, Python 3.12 oder neuer.
- **Nicht enthalten:** FastAPI-App, `MongoRepository`, Import-Skript für Mongo, Filter im Browser, englische Inhalte.

## Further Considerations

1. **Ausblick dynamische App:**
   - `MongoRepository` implementiert dasselbe Protocol `Repository`.
   - Ein Seed-Befehl `tastingsets seed-mongo` liest die JSON-Dateien über `JsonRepository`, validiert sie und spielt sie per Upsert nach `_id` ein.
   - FastAPI-Routen verwenden `Catalog`, `stats` und dieselben Templates.
   - Da MongoDB keine Referenzen prüft, läuft `validate` dann als Admin- oder CI-Befehl gegen die Datenbank.
2. **Weitere Felder für später**, z.B. `volume_ml` und `cask` am Spirit oder `opened_on` am Member: `extra="forbid"` sorgt dafür, dass so etwas bewusst im Modell ergänzt wird. Vorschlag: zunächst weglassen.
3. **Sortierung der Member:** Reihenfolge wie in der Datei (empfohlen, Standard) oder natürliche Sortierung nach `member_id` (1, 2, … 10 statt 1, 10, 2). Kann man im Template umschaltbar machen.
