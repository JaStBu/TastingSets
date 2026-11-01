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
| `tastingsets build [--data DIR] [--out DIR] [--base-url /TastingSets/] [--languages LANG ...]` | Validates and generates the static site. By default, builds every language with a JSON file in `locales/`; `--languages` selects a subset. Aborts on errors. |
| `tastingsets schema [--out DIR]` | Writes the JSON schemas to `schemas/` (optional, editor support only, see [Editor support](#editor-support-optional)). |

## Data model

Each folder under `data/` is one collection (= later one MongoDB collection). Inside a folder, all `*.json` files are loaded in alphabetical order, so a collection may be split over many files (`a-m.json`, `n-z.json`, ...). A file contains one object or a list of objects. Every document has an `_id` that is a lowercase slug (`ardbeg`, `ardbeg-10`).

| Folder | Document | Fields |
| --- | --- | --- |
| `data/categories/` | kind of spirit | `_id`, `names` (language → name, default language required) |
| `data/distilleries/` | distillery | `_id`, `name`, `display_name`?, `country` (ISO 3166-1 alpha-2 such as `DE`, or ISO 3166-2 such as `GB-SCT`), `region`? (free text for non-ISO regions such as `Islay` or `Speyside`, not translated) |
| `data/spirits/` | spirit | `_id`, `name`, `display_name`?, `category_id`, `abv` (0–100), `distillery_id`?, `distillery_name`?, `url`? |
| `data/tasting_sets/` | tasting set | `_id`, `names` (language → name, default language required), `year`?, and **either** `members` **or** `groups` |

A *set member* is embedded in its tasting set: `member_id` (string), `spirit_id`, `notes`? (language → text, same format as `names`).

- `member_id` is unique inside a set (also across groups). Across sets, a member is identified by its fully qualified name `<set_id>/<member_id>`, e.g. `advent-2026/24`.
- **Names:** distillery and spirit names are proper nouns and are not translated (`name`, optional `display_name`). Tasting set names, group names and member notes are localized (`names`, `description`, `notes`), because they are descriptive text.
- **Groups (optional):** a set can be divided into display-only sub-groups, e.g. 4 groups of 3 bottles. Instead of `members`, the set then has `groups`, each with `group_id`, `names` (language → name, default language required), `description`? (same format) and its own `members`. So either all bottles of a set are in a group or none. Groups are shown on the set page (header row per group plus a sentence like "2 groups of 3 bottles each") and as a count on the overview page. They have no influence on statistics. Order is preserved: groups as defined, members as in the file.

```json
{
  "_id": "advent-2026",
  "names": { "de": "Adventskalender 2026", "en": "Advent Calendar 2026" },
  "groups": [
    {
      "group_id": "wine-finish",
      "names": { "de": "Weinfinish", "en": "Wine finish" },
      "description": { "de": "Gereift in Weinfässern" },
      "members": [
        { "member_id": "1", "spirit_id": "ardbeg-10" },
        { "member_id": "2", "spirit_id": "ardbeg-uigeadail", "notes": { "de": "Fassstärke" } }
      ]
    }
  ]
}
```
- A spirit needs `distillery_id` **or** `distillery_name`. If the distillery has no entry in `data/distilleries/`, only give `distillery_name`; this is allowed but produces the warning `MISSING_DISTILLERY_ENTRY`. A `distillery_id` that does not exist is an error (probably a typo).
- Unknown fields are rejected, so typos in field names are found.

### Languages

The default language is defined once in `src/tastingsets/languages.py` (currently `de`). It is required in every localized field (`names`, `description`, `notes`), it is the fallback for localized content and UI strings, it must always be built, and `/index.html` redirects to it. To use another default language (e.g. Spanish), change `DEFAULT_LANGUAGE`, add `locales/es.json` with the same keys as the other locale files, and add the language to all localized fields in `data/` (`uv run tastingsets validate` lists every affected document).

### Validation

| Severity | Code | Meaning |
| --- | --- | --- |
| error | `INVALID_JSON` | file is not valid JSON |
| error | `SCHEMA` | a document violates the data model |
| error | `DUPLICATE_ID` | `_id` used twice in a collection (also across files) |
| error | `DUPLICATE_MEMBER_ID` | `member_id` used twice in one set (also across groups) |
| error | `DUPLICATE_GROUP_ID` | `group_id` used twice in one set |
| error | `UNKNOWN_CATEGORY` / `UNKNOWN_DISTILLERY` / `UNKNOWN_SPIRIT` | reference to a non-existing document |
| warning | `MISSING_DISTILLERY_ENTRY` | spirit names a distillery that has no entry |
| warning | `DISTILLERY_NAME_MATCHES_ENTRY` | `distillery_name` equals an existing distillery; use `distillery_id` |
| warning | `UNUSED_SPIRIT` | spirit is not part of any set |

## Adding data

- **New spirit:** add an object to a file in `data/spirits/` (or create a new file there). Use `distillery_id` if the distillery exists in `data/distilleries/`, otherwise `distillery_name`.
- **New tasting set:** create `data/tasting_sets/<set-id>.json` with `names` and the members in the order they should be displayed. Use `groups` instead of `members` if the set consists of sub-groups.
- Run `uv run tastingsets validate` before pushing. This is the actual data check: it uses the Pydantic models, so it also finds problems that JSON schemas cannot express (references between files, duplicate ids, country codes, ...).

### Editor support (optional)

VS Code can validate and auto-complete the data files while you type. For that, generate the JSON schemas once:

```sh
uv run tastingsets schema
```

`.vscode/settings.json` maps each folder in `data/` to its schema in `schemas/`. The `schemas/` folder is generated from the Pydantic models, ignored by git and not needed for `validate`, `build`, tests or CI. Run the command again after changing `src/tastingsets/models.py`. Without the schemas, VS Code simply shows no hints.

## Versioning and releases

The package version is not stored in `pyproject.toml`. It is derived from Git tags of the form `vX.Y.Z` by [hatch-vcs](https://github.com/ofek/hatch-vcs) (`[tool.hatch.version] source = "vcs"`):

| Git state | `__version__` |
| --- | --- |
| commit is tagged `v0.2.0` | `0.2.0` |
| 3 commits after `v0.2.0` | `0.2.1.dev3+g1a2b3c4` |
| uncommitted changes | additionally `+d<date>` |

- **Release:** create a tag and push it (`git tag v0.2.0 && git push origin v0.2.0`), or create a release with the tag `v0.2.0` in the GitHub UI. No file has to be changed, and `uv.lock` stays valid: for a dynamic version, uv does not store the project's own version in the lock file.
- **CI:** `actions/checkout` uses `fetch-depth: 0`, otherwise the tags are missing and the version is wrong.
- **Local:** the `cache-keys` in `[tool.uv]` make `uv sync` rebuild the editable install after a new commit or tag. Otherwise run `uv sync --reinstall-package tastingsets`.
- **Site:** the footer shows `TastingSets vX.Y.Z` with a link to the repository (`[project.urls]` in `pyproject.toml`). Without an installed package the version is `unknown` and is omitted.

## Publishing (GitHub Pages)

- `.github/workflows/ci.yml` (job `check`) does lint, format check, tests, data validation (warnings appear as annotations, the job stays green) and a test build. It runs when a pull request is opened, when commits are pushed to a branch with an open pull request, and when a pull request is reopened. It is also a reusable workflow (`workflow_call`).
- `.github/workflows/pages.yml` runs on every push to `main` (and manually). It first calls `ci.yml`; only if the check is green, it builds the site and deploys it to GitHub Pages. A push to `main` is therefore checked exactly once, and a failing check never gets published.
- A push to a feature branch **without** a pull request runs nothing; open a pull request to get the check.
- Recommended: in *Settings → Branches* (or *Rulesets*), require the status check `check` for `main`, so a pull request with a failing check cannot be merged.
- **One-time setup:** in the repository, go to *Settings → Pages* and set *Source* to **GitHub Actions**.

The site is then available at `https://<user>.github.io/TastingSets/`.

## Architecture and outlook

```
models → repository (JSON files) → catalog → validation / stats / site builder (Jinja2, i18n)
```

The JSON files have the same structure as the MongoDB documents (`model_dump()` produces `_id`). For the dynamic app only a `MongoRepository` implementing the `Repository` protocol (`src/tastingsets/repository/base.py`) and a web layer (e.g. FastAPI) that reuses `Catalog`, `stats` and the templates are needed. A `seed-mongo` command could import the JSON files into the database. Since MongoDB does not check references, `validate` should then also be run against the database.

**Package releases (required with a database).** As long as the data lives in this repository, every push to `main` is a complete release: code and data are published together by `pages.yml`. Once the data moves to a database, the repository only contains code, and the app (and the generated site) is deployed from a released package version instead of the current state of `main`. Releases are then a requirement, not an option:

- *Release workflow (planned, not implemented yet):* a workflow `.github/workflows/release.yml` triggered by `push` of tags `v*`. It checks out with `fetch-depth: 0`, runs `uv build` and creates a GitHub release with wheel and sdist attached. Publishing to PyPI via trusted publishing can be added to the same workflow if the package is meant to be used by others.
- *Deployment:* installs the released version (a fixed tag) rather than building from `main`, so code and database schema stay in step.
- *Versioning:* the tag defines the version, see [Versioning and releases](#versioning-and-releases). A change to the data contract (models) should result in a new release.

A tasting set document contains either `members` or `groups[].members`. Queries over all bottles (statistics) must therefore not read `members` directly, but go through `Catalog` / `TastingSet.all_members`, or the `MongoRepository` stores a flat member list in addition when writing; decide this when the `MongoRepository` is implemented. The group is deliberately not part of the fully qualified member name (`<set_id>/<member_id>`): the number is already unique in the set, and links stay stable if groups are rearranged.

**Region statistics (planned, not implemented yet).** Besides the existing statistics per country (`count_by_country`, counted by the exact `country` code, so `GB` and `GB-SCT` are separate entries), there should be a second evaluation per region, i.e. bottles per `region` of the distillery (e.g. `Islay`, `Speyside`):

- *Data:* uses the optional free-text `region` field of `data/distilleries/`. Bottles whose distillery has no entry or no `region` are grouped under `unknown`, like in the country statistics.
- *Code:* a new function `count_by_region(catalog, set_ids)` in `src/tastingsets/stats.py` with the same signature and `CountEntry` result as `count_by_country`, and a new field `by_region` in `StatsReport`.
- *Site:* an additional table "Bottles per region" (`stats.by_region` in `locales/*.json`) next to "Bottles per country" in the statistics macros, for each set and for all sets.
- *Open point:* `region` is free text, so spelling variants (`Islay` vs. `islay`) count as separate entries unless they are compared case-insensitively, as `count_by_distillery` does for `distillery_name`.

**Configurable default language (not implemented yet).** Today the default language is a constant in `src/tastingsets/languages.py`; changing it means changing code. If the project is used as a package by others, it could become a setting instead:

- *Where:* the setting belongs to the data contract, not to the build, because changing it invalidates existing data. Candidates are a file next to the collections, e.g. `data/settings.json` (not loaded as a collection), or `[tool.tastingsets] default_language` in `pyproject.toml`. With MongoDB, it would be a settings document.
- *Validation:* Pydantic receives the language via the validation context (`model_validate(..., context={"default_language": ...})`, read in the validator via `ValidationInfo.context`) instead of the module constant. `JsonRepository` and later `MongoRepository` pass it through.
- *Other layers:* `i18n`, `stats` and the site builder receive the language as a parameter instead of importing the constant. Because the constant is used in one place only, this is a contained change.
- *Switching:* existing data must be migrated; `validate` shows every document that lacks the new default language.

Implement this only when there is a concrete need.
