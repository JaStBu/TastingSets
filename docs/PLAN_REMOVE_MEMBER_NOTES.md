# Plan: Notizen der Tasting-Set-Member entfernen

## Ziel und Umfang

Das optionale Feld `notes` an Set Members wird vollständig aus dem Projekt entfernt: aus dem
Datenmodell, der Katalog-Schicht, der Set-Seite, den Locale-Dateien, den echten Daten, den Tests
und der Dokumentation. Ein Tasting-Set-Dokument, das weiterhin `notes` enthält, ist danach ein
Schemafehler (`SCHEMA`), weil `SetMember` über `_Strict` mit `extra="forbid"` validiert wird.

Begründung: Die Notizen sind reiner Freitext ohne Auswirkung auf Statistik oder Navigation, werden
nur in einer Tabellenspalte angezeigt und sind in den Daten nur in vier Sets gepflegt. Das Feld
verkleinert das Datenmodell und die Set-Seite.

**In Scope**

- `SetMember.notes` in `src/tastingsets/models.py`
- `ResolvedMember.notes` in `src/tastingsets/catalog.py`
- Spalte „Anmerkung“ in `src/tastingsets/site/templates/set.html` (inkl. `colspan`)
- Locale-Schlüssel `table.notes` in `locales/de.json` und `locales/en.json`
- 80 `notes`-Einträge in `data/tasting_sets/advent-2019.json`, `advent-2020.json`,
  `advent-2021.json`, `advent-2022.json`
- Tests und Fixtures, die `notes` verwenden
- README und `docs/IMPLEMENTATION_PLAN.md`

**Out of Scope**

- `LocalizedText` bleibt unverändert bestehen (genutzt von `Category.names`, `TastingSet.names`,
  `SetGroup.names`, `SetGroup.description`).
- Gruppenbeschreibungen (`SetGroup.description`) bleiben erhalten – sie sind kein Member-Feld.
- Keine Migration der Notiztexte in andere Felder oder Dateien (die Git-Historie genügt).
- Keine Änderung an Statistik, Validierungs-Codes, CLI, Repository, Schemas-Generator, CI.
- Keine neuen Abhängigkeiten, keine Umbenennung von Modulen.

## Akzeptanzkriterien

1. `SetMember` hat kein Feld `notes` mehr; `SetMember.model_validate({"member_id": "1",
   "spirit_id": "a", "notes": {"de": "x"}})` wirft `pydantic.ValidationError`.
2. `ResolvedMember` hat kein Attribut `notes`; `Catalog.resolve_member(...)` liefert ein Objekt
   ohne dieses Feld.
3. Die Set-Seite enthält weder die Überschrift „Anmerkung“/„Notes“ noch eine Notizspalte; die
   Gruppenzelle hat `colspan="8"` statt `colspan="9"`.
4. `locales/de.json` und `locales/en.json` enthalten keinen Schlüssel `table.notes`; beide Dateien
   haben weiterhin identische Schlüsselmengen (`tests/test_i18n.py` bleibt grün).
5. In `data/tasting_sets/*.json` kommt der String `notes` nicht mehr vor; `uv run tastingsets
   validate` meldet für `data/` keine Fehler.
6. `uv run pytest` ist grün (152 Tests), `uv run ruff check` und `uv run ruff format --check` sind
   ohne Befund.
7. `uv run tastingsets build --out dist` läuft durch; die erzeugten Set-Seiten enthalten keine
   Notizspalte.
8. Im Repository (außer diesem Plan) verweist nichts mehr auf Member-Notizen: `grep -rn '"notes"'
   src tests locales data README.md docs/IMPLEMENTATION_PLAN.md` liefert keine Treffer.

## Relevante Dateien

**Zu ändern**

| Datei | Änderung |
| --- | --- |
| `src/tastingsets/models.py` | Feld `notes` aus `SetMember` entfernen (Zeile mit `notes: LocalizedText \| None = None`) |
| `src/tastingsets/catalog.py` | Feld `notes` aus `ResolvedMember` und das Argument `notes=member.notes` in `Catalog.resolve` entfernen |
| `src/tastingsets/site/templates/set.html` | `<th>{{ t('table.notes') }}</th>`, die `<td>`-Zelle mit `localized_text(m.notes)` und `colspan="9"` → `colspan="8"` |
| `locales/de.json` | Schlüssel `"table.notes": "Anmerkung"` entfernen |
| `locales/en.json` | Schlüssel `"table.notes": "Notes"` entfernen |
| `data/tasting_sets/advent-2019.json` | 16 `notes`-Einträge entfernen |
| `data/tasting_sets/advent-2020.json` | 16 `notes`-Einträge entfernen |
| `data/tasting_sets/advent-2021.json` | 24 `notes`-Einträge entfernen |
| `data/tasting_sets/advent-2022.json` | 24 `notes`-Einträge entfernen |
| `tests/conftest.py` | `notes` aus dem Member `2` in `TASTING_SETS` entfernen |
| `tests/test_models.py` | `test_set_member_notes_are_localized` durch `test_set_member_rejects_notes` ersetzen |
| `tests/test_catalog.py` | `assert member.notes == {"de": "cask strength"}` entfernen |
| `tests/test_builder.py` | `assert "cask strength" in html` entfernen, `test_set_name_and_notes_are_localized` → `test_set_name_is_localized` (Notiz-Assertion raus, Assertion „keine Notizspalte“ rein) |
| `tests/test_json_repository.py` | neuer Test: `notes` in einem Set führt zu `SCHEMA` in `load_errors` |
| `README.md` | Member-Beschreibung, Lokalisierungsabsatz, JSON-Beispiel, Sprachabschnitt |
| `docs/IMPLEMENTATION_PLAN.md` | Beispiel-JSON, `SetMember`-Beschreibung, `ResolvedMember`-Felder, Entscheidungsabschnitt |

**Nicht anzufassen**

`src/tastingsets/stats.py`, `src/tastingsets/validation.py`, `src/tastingsets/i18n.py`,
`src/tastingsets/repository/*`, `src/tastingsets/cli.py`, `src/tastingsets/schemas.py`,
`src/tastingsets/languages.py`, `src/tastingsets/site/builder.py`, `src/tastingsets/site/static/style.css`,
`tests/fixtures/data/**`, `tests/test_groups.py`, `tests/test_stats.py`, `tests/test_validation.py`,
`tests/test_i18n.py`, `tests/test_cli.py`, `tests/test_schemas.py`, `.github/**`, `pyproject.toml`.

`schemas/` ist per `.gitignore` ausgeschlossen und wird nur lokal neu erzeugt (siehe Phase 4).

## Umsetzungsphasen

### Phase 1 – Modell und Katalog

Konkrete Änderungen:

1. `src/tastingsets/models.py`: in `SetMember` die Zeile `notes: LocalizedText | None = None`
   löschen. `LocalizedText` bleibt definiert und wird weiter von `Category`, `SetGroup` und
   `TastingSet` genutzt. Docstring von `SetMember` bleibt unverändert (nennt keine Notizen).
2. `src/tastingsets/catalog.py`: in `ResolvedMember` das Feld `notes: dict[str, str] | None`
   löschen und in `Catalog.resolve` das Argument `notes=member.notes,` entfernen. Reihenfolge der
   übrigen Felder beibehalten.
3. `tests/conftest.py`: Member `2` in `TASTING_SETS[0]` auf
   `{"member_id": "2", "spirit_id": "secret-12"}` reduzieren.
4. `tests/test_catalog.py`: in `test_resolve_member_without_distillery_entry` die Zeile
   `assert member.notes == {"de": "cask strength"}` entfernen (die übrigen Assertions bleiben).
5. `tests/test_models.py`: `test_set_member_notes_are_localized` ersetzen durch

   ```python
   def test_set_member_rejects_notes():
       with pytest.raises(ValidationError):
           SetMember.model_validate(
               {"member_id": "1", "spirit_id": "a", "notes": {"de": "Fassstärke"}}
           )
   ```

   (Muster: bestehende Tests in derselben Datei, z. B. `test_tasting_set_rejects_duplicate_member_ids`.)

Prüfen: `uv run pytest tests/test_models.py tests/test_catalog.py tests/test_groups.py -q`
→ grün. `uv run ruff check src tests` → keine Befunde.

### Phase 2 – Template und Locales

Konkrete Änderungen:

1. `src/tastingsets/site/templates/set.html`:
   - `<th>{{ t('table.notes') }}</th>` aus dem `<thead>` entfernen.
   - `<td>{{ localized_text(m.notes) if m.notes else '' }}</td>` aus der Member-Zeile entfernen.
   - `colspan="9"` in der Gruppenkopfzeile auf `colspan="8"` ändern (die Tabelle hat danach
     8 Spalten: Nr., Schnaps, Art, Brennerei, Land, Region, Alkohol, Link).
   - `localized_text` bleibt in Gebrauch (Set-Name, Gruppenname, Gruppenbeschreibung).
2. `locales/de.json` und `locales/en.json`: Zeile `"table.notes": ...` entfernen. Die
   Schlüsselmengen beider Dateien müssen identisch bleiben (`tests/test_i18n.py::
   test_all_locales_have_same_keys_as_default`).
3. `tests/test_builder.py`:
   - In `test_set_page_lists_members_with_details` die Zeile `assert "cask strength" in html`
     entfernen und stattdessen `assert "Anmerkung" not in html` ergänzen.
   - `test_set_name_and_notes_are_localized` umbenennen in `test_set_name_is_localized`, die
     Notiz-Assertion (`assert "cask strength" in de and "cask strength" in en`) entfernen; die
     Assertions zu Set-Namen und Rückfall bleiben.

Prüfen: `uv run pytest tests/test_builder.py tests/test_i18n.py tests/test_groups.py -q` → grün.

### Phase 3 – Daten

Konkrete Änderungen: In den vier Dateien `data/tasting_sets/advent-2019.json`,
`advent-2020.json`, `advent-2021.json`, `advent-2022.json` jeweils alle `notes`-Einträge
entfernen. Die Einträge stehen immer als letztes Feld eines Member-Objekts und enthalten keine
geschweiften Klammern oder Anführungszeichen im Text, daher ist ein einmaliges Skript sicher:

```sh
uv run python - <<'PY'
import json, re, pathlib

pattern = re.compile(r',\s*"notes":\s*\{[^{}]*\}')
for name in ("advent-2019", "advent-2020", "advent-2021", "advent-2022"):
    path = pathlib.Path(f"data/tasting_sets/{name}.json")
    text = path.read_text(encoding="utf-8")
    updated = pattern.sub("", text)
    json.loads(updated)  # bricht ab, falls das Ergebnis ungültig wäre
    path.write_text(updated, encoding="utf-8")
PY
```

(Ohne `uv` im PATH: `.venv/bin/python - <<'PY'` mit demselben Skript. Es entsteht keine temporäre
Datei.)

Danach bleiben Member-Zeilen wie `{ "member_id": "1", "spirit_id": "ardbeg-10" }` bzw. bei
mehrzeiligen Objekten ein Objekt mit `member_id` und `spirit_id` – dieselbe Form wie in
`data/tasting_sets/advent-2026.json`. Kein weiteres Umformatieren, keine Sortierung.

Zusätzlich in `tests/test_json_repository.py` einen Test ergänzen (Muster:
`test_duplicate_member_id_has_own_code`):

```python
def test_notes_field_is_reported_as_schema_error(tmp_path):
    ts = {
        "_id": "with-notes",
        "names": {"de": "Mit Notizen"},
        "members": [{"member_id": "1", "spirit_id": "ardbeg-10", "notes": {"de": "x"}}],
    }
    repo = JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts]))
    assert [e.code for e in repo.load_errors] == ["SCHEMA"]
    assert repo.tasting_sets() == []
```

Prüfen: `grep -c notes data/tasting_sets/*.json` → alle Dateien `0`.
`uv run pytest tests/test_json_repository.py -q` → grün.
`uv run tastingsets validate` → keine Fehler (Warnungen wie `MISSING_DISTILLERY_ENTRY` sind
erlaubt).

### Phase 4 – Dokumentation und lokale Schemas

Konkrete Änderungen:

1. `README.md`:
   - Abschnitt „Data model“, Member-Zeile: „A *set member* is embedded in its tasting set:
     `member_id` (string), `spirit_id`.“ (kein `notes` mehr).
   - Aufzählung „**Names:**“: „Tasting set names and group names/descriptions are localized
     (`names`, `description`), because they are descriptive text.“ – Member-Notizen entfallen.
   - JSON-Beispiel: Member `2` auf `{ "member_id": "2", "spirit_id": "ardbeg-uigeadail" }`
     reduzieren.
   - Abschnitt „Languages“: `notes` aus der Liste der lokalisierten Pflichtfelder streichen
     (bleibt `names`, `description`).
2. `docs/IMPLEMENTATION_PLAN.md`:
   - Beispiel-JSON in „Beispiel-Datenformat“: `notes` beim Member `2` entfernen.
   - Phase 2, Punkt 7 (`SetMember`): `spirit_id: str` ohne `notes`-Nachtrag.
   - Phase 3, Punkt 11 (`ResolvedMember`): `notes` aus der Feldliste entfernen.
   - Abschnitt „Decisions“: einen Satz ergänzen: „Set Member haben keine Notizen; das frühere
     Feld `notes` wurde entfernt, Dokumente mit `notes` sind ein Schemafehler (`SCHEMA`).“
3. Lokal (nicht versioniert, `schemas/` ist in `.gitignore`): `uv run tastingsets schema`
   ausführen, damit die Editor-Hinweise nicht mehr auf `notes` verweisen.

Prüfen: `grep -rn '"notes"' README.md docs/IMPLEMENTATION_PLAN.md` → keine Treffer.
`uv run pytest -q` → 152 Tests grün.

## Verifikation

1. `uv run pytest -q` → `152 passed` (vorher 151; −1 entfernter Notiz-Test, +1 neuer
   Modell-Test, +1 neuer Repository-Test, ein Test wurde nur umbenannt).
2. `uv run ruff check` → keine Befunde.
3. `uv run ruff format --check` → keine Änderungen nötig.
4. `uv run tastingsets validate` → Exit-Code 0, keine `error`-Zeilen.
5. `grep -c notes data/tasting_sets/*.json` → für alle elf Dateien `0`.
6. `grep -rn '"notes"' src tests locales data README.md docs/IMPLEMENTATION_PLAN.md` → keine
   Treffer.
7. `uv run tastingsets build --out dist` → Exit-Code 0, „wrote …“ in der Ausgabe.
8. `grep -c 'Anmerkung\|table.notes' dist/de/sets/advent-2021/index.html` → `0`; zusätzlich
   `grep -c 'colspan="8"' dist/de/sets/advent-2021/index.html` → `1` (manuelle Sichtprüfung
   optional: `python -m http.server -d dist`, Set-Seite ohne Notizspalte).
9. `uv run tastingsets schema` → Exit-Code 0; `grep -c notes schemas/tasting_sets.schema.json`
   → `0` (nur lokal, nicht versioniert).
10. `git status --short` → nur die in „Relevante Dateien“ genannten Dateien sind geändert
    (keine Commits, keine Index-Änderungen).

## Annahmen, Risiken und offene Punkte

- **Annahme:** Die Notiztexte werden verworfen; die Git-Historie gilt als ausreichende Sicherung
  (so mit dem Auftraggeber abgestimmt).
- **Annahme:** `notes` in Daten ist ein Fehler, keine Warnung – konsistent zu `extra="forbid"` in
  `_Strict`. Es wird kein neuer Validierungs-Code eingeführt; der bestehende Code `SCHEMA` greift.
- **Annahme:** `LocalizedText` und `SetGroup.description` bleiben, weil sie unabhängig von
  Member-Notizen genutzt werden.
- **Risiko:** Fremde Datenstände oder Forks mit `notes` werden nach dem Update ungültig. Das ist
  gewollt und wird durch `validate` mit `SCHEMA` und Dateiname gemeldet; die Fehlermeldung nennt
  das Feld `notes`.
- **Risiko:** Wird das Entfernungsskript auf weitere Dateien angewendet, die `notes` in anderem
  Kontext enthalten (z. B. `spirits`), würde es zu viel löschen. Deshalb ist die Dateiliste im
  Skript fest verdrahtet.
- **Offener Punkt:** `schemas/` ist lokal vorhanden, aber nicht versioniert; ohne erneutes
  `tastingsets schema` zeigt der Editor weiterhin `notes` an. Kein Fehler, nur Komfort.
- **Umgebung:** `uv` ist in dieser Umgebung nicht im PATH; die Befehle funktionieren ersatzweise
  über `.venv/bin/python -m pytest`, `.venv/bin/python -m ruff` und
  `.venv/bin/python -m tastingsets`.

## Auswirkungen auf die Dokumentation

**`README.md`** – der Member eines Tasting Sets besteht nur noch aus `member_id` und `spirit_id`;
es gibt kein Feld für Notizen. Lokalisiert sind weiterhin Set-Namen (`names`) sowie
Gruppennamen und -beschreibungen (`names`, `description`); die Standardsprache ist in diesen
Feldern Pflicht. Das JSON-Beispiel zeigt Member ohne `notes`. Ein Set-Dokument mit `notes` wird
von `tastingsets validate` als Schemafehler abgelehnt, weil unbekannte Felder generell verboten
sind.

**`docs/IMPLEMENTATION_PLAN.md`** – `SetMember` hat die Felder `member_id` und `spirit_id`;
`ResolvedMember` führt kein `notes`-Feld. Die Beispiel-Dokumente enthalten keine Notizen. Im
Abschnitt „Decisions“ ist festgehalten, dass Set Member keine Notizen haben und das frühere Feld
`notes` entfernt wurde; Dokumente mit `notes` sind ein Schemafehler (`SCHEMA`).
