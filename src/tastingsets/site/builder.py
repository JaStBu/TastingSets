"""Static site generator: renders Jinja2 templates into an output directory."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from babel.numbers import format_decimal
from jinja2 import Environment, FileSystemLoader

from tastingsets.catalog import Catalog
from tastingsets.i18n import DEFAULT_LOCALES_DIR, Translator, country_name, localized
from tastingsets.repository.base import Repository
from tastingsets.stats import build_report
from tastingsets.validation import Issue, has_errors, validate

SITE_DIR = Path(__file__).parent
TEMPLATES_DIR = SITE_DIR / "templates"
STATIC_DIR = SITE_DIR / "static"


class BuildError(Exception):
    """Raised when the data contains errors; the site is not generated."""

    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        super().__init__(f"data validation failed with {len(issues)} issue(s)")


@dataclass(frozen=True)
class SetListEntry:
    set_id: str
    label: str
    year: int | None
    bottle_count: int


def normalize_base_url(base_url: str) -> str:
    """Return the base URL with exactly one leading and one trailing slash."""
    stripped = base_url.strip("/")
    return f"/{stripped}/" if stripped else "/"


def make_environment(base_url: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    base = normalize_base_url(base_url)
    env.globals["url_for"] = lambda path="": base + path.lstrip("/")
    return env


def build(
    repo: Repository,
    out_dir: Path | str,
    base_url: str = "/",
    languages: Sequence[str] = ("de",),
    locales_dir: Path | str = DEFAULT_LOCALES_DIR,
) -> list[Path]:
    """Generate the site and return all written files.

    Raises :class:`BuildError` if the data has validation errors (warnings are fine).
    """
    issues = validate(repo)
    if has_errors(issues):
        raise BuildError(issues)
    if not languages:
        raise ValueError("at least one language is required")

    catalog = Catalog.from_repository(repo)
    env = make_environment(base_url)
    out = Path(out_dir)
    written: list[Path] = []

    def render(template: str, target: Path, context: dict[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(**context), encoding="utf-8")
        written.append(target)

    render("redirect.html", out / "index.html", {"target": f"{languages[0]}/"})

    for lang in languages:
        translator = Translator(lang, locales_dir)

        def context(
            page_path: str, *, lang: str = lang, translator: Translator = translator, **extra: Any
        ) -> dict[str, Any]:
            # lang/translator are bound as defaults so that each loop iteration keeps its own.
            return {
                "lang": lang,
                "languages": list(languages),
                "page_path": page_path,
                "t": translator.t,
                "category_name": lambda category: localized(category.names, lang),
                "country_name": lambda code: country_name(code, lang),
                "format_abv": lambda value: _format_abv(value, lang),
                **extra,
            }

        lang_dir = out / lang
        entries = [
            SetListEntry(ts.id, ts.label, ts.year, len(ts.members))
            for ts in catalog.tasting_sets.values()
        ]
        overall = build_report(catalog, None, lang)
        render(
            "index.html",
            lang_dir / "index.html",
            context("", entries=entries, report=overall),
        )
        render("stats.html", lang_dir / "stats" / "index.html", context("stats/", report=overall))
        for tasting_set in catalog.tasting_sets.values():
            render(
                "set.html",
                lang_dir / "sets" / tasting_set.id / "index.html",
                context(
                    f"sets/{tasting_set.id}/",
                    tasting_set=tasting_set,
                    members=catalog.resolve_set(tasting_set.id),
                    report=build_report(catalog, [tasting_set.id], lang),
                ),
            )

    static_target = out / "static"
    shutil.copytree(STATIC_DIR, static_target, dirs_exist_ok=True)
    written.extend(p for p in static_target.rglob("*") if p.is_file())
    return written


def _format_abv(value: float, lang: str) -> str:
    return f"{format_decimal(value, format='0.0#', locale=lang)} %"
