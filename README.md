# TastingSets

Overview of the contents of various tasting sets (e.g. advent calendars): which bottle number contains which spirit, and statistics over all sets. The site is generated as static HTML and published with GitHub Pages. The data model is prepared for a later dynamic web app with MongoDB.

The full design is described in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                       # install dependencies
uv run pytest                 # run the tests
uv run tastingsets validate   # check the data in data/
uv run tastingsets build      # generate the site into dist/
python -m http.server -d dist # local preview, see http://localhost:8000/de/
```

Commands:

| Command | Purpose |
| --- | --- |
| `tastingsets validate [--data DIR] [--strict]` | Validates all data files. Exit code 1 on errors (with `--strict` also on warnings). Inside GitHub Actions, findings are also printed as annotations. |
| `tastingsets build [--data DIR] [--out DIR] [--base-url /TastingSets/] [--languages de en]` | Validates and generates the static site. Aborts on errors. |
| `tastingsets schema [--out DIR]` | Writes the JSON schemas to `schemas/` (used for editor support, see `.vscode/settings.json`). Re-run after changing `models.py`. |

## Data model

Each folder under `data/` is one collection (= later one MongoDB collection). Inside a folder, all `*.json` files are loaded in alphabetical order, so a collection may be split over many files (`a-m.json`, `n-z.json`, ...). A file contains one object or a list of objects. Every document has an `_id` that is a lowercase slug (`ardbeg`, `ardbeg-10`).

| Folder | Document | Fields |
| --- | --- | --- |
| `data/categories/` | kind of spirit | `_id`, `names` (language → name, `de` required) |
| `data/distilleries/` | distillery | `_id`, `name`, `display_name`?, `country` (ISO 3166-1 alpha-2, e.g. `GB`) |
| `data/spirits/` | spirit | `_id`, `name`, `display_name`?, `category_id`, `abv` (0–100), `distillery_id`?, `distillery_name`?, `url`? |
| `data/tasting_sets/` | tasting set | `_id`, `name`, `display_name`?, `year`?, `members` |

A *set member* is embedded in its tasting set: `member_id` (string), `spirit_id`, `notes`?.

- `member_id` is unique inside a set. Across sets, a member is identified by its fully qualified name `<set_id>/<member_id>`, e.g. `advent-2026/24`.
- A spirit needs `distillery_id` **or** `distillery_name`. If the distillery has no entry in `data/distilleries/`, only give `distillery_name`; this is allowed but produces the warning `MISSING_DISTILLERY_ENTRY`. A `distillery_id` that does not exist is an error (probably a typo).
- Unknown fields are rejected, so typos in field names are found.

### Validation

| Severity | Code | Meaning |
| --- | --- | --- |
| error | `INVALID_JSON` | file is not valid JSON |
| error | `SCHEMA` | a document violates the data model |
| error | `DUPLICATE_ID` | `_id` used twice in a collection (also across files) |
| error | `DUPLICATE_MEMBER_ID` | `member_id` used twice in one set |
| error | `UNKNOWN_CATEGORY` / `UNKNOWN_DISTILLERY` / `UNKNOWN_SPIRIT` | reference to a non-existing document |
| warning | `MISSING_DISTILLERY_ENTRY` | spirit names a distillery that has no entry |
| warning | `DISTILLERY_NAME_MATCHES_ENTRY` | `distillery_name` equals an existing distillery; use `distillery_id` |
| warning | `UNUSED_SPIRIT` | spirit is not part of any set |

## Adding data

- **New spirit:** add an object to a file in `data/spirits/` (or create a new file there). Use `distillery_id` if the distillery exists in `data/distilleries/`, otherwise `distillery_name`.
- **New tasting set:** create `data/tasting_sets/<set-id>.json` with the members in the order they should be displayed.
- Run `uv run tastingsets validate` before pushing. With the JSON schemas, VS Code also validates and completes while typing.

## Publishing (GitHub Pages)

- `.github/workflows/ci.yml` runs on every branch except `main` and on pull requests: lint, tests, data validation (warnings appear as annotations, the job stays green) and a test build.
- `.github/workflows/pages.yml` runs on every push to `main`: tests, validation, build and deployment to GitHub Pages.
- **One-time setup:** in the repository, go to *Settings → Pages* and set *Source* to **GitHub Actions**.

The site is then available at `https://<user>.github.io/TastingSets/`.

## Architecture and outlook

```
models → repository (JSON files) → catalog → validation / stats / site builder (Jinja2, i18n)
```

The JSON files have the same structure as the MongoDB documents (`model_dump()` produces `_id`). For the dynamic app only a `MongoRepository` implementing the `Repository` protocol (`src/tastingsets/repository/base.py`) and a web layer (e.g. FastAPI) that reuses `Catalog`, `stats` and the templates are needed. A `seed-mongo` command could import the JSON files into the database. Since MongoDB does not check references, `validate` should then also be run against the database.
