"""Statistics over tasting sets (pure functions on a :class:`Catalog`).

Every function takes ``set_ids``: the sets to include, or ``None`` for all sets.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from tastingsets.catalog import Catalog, ResolvedMember
from tastingsets.languages import DEFAULT_LANGUAGE
from tastingsets.models import Spirit

#: Key used for members whose country is not known (no distillery entry).
UNKNOWN_KEY = "unknown"


@dataclass(frozen=True)
class CountEntry:
    """``key`` identifies the group (an ``_id`` or ``unknown``), ``label`` is its display text."""

    key: str
    label: str
    count: int


@dataclass(frozen=True)
class RepeatedSpirit:
    """A spirit that occurs more than once, with all places where it occurs."""

    spirit: Spirit
    count: int
    fqns: tuple[str, ...]
    set_ids: tuple[str, ...]


@dataclass(frozen=True)
class AbvSummary:
    minimum: float
    maximum: float
    mean: float


@dataclass(frozen=True)
class Totals:
    sets: int
    members: int
    distinct_spirits: int


def selected_members(
    catalog: Catalog, set_ids: Iterable[str] | None = None
) -> list[ResolvedMember]:
    """All resolved members of the selected sets (all sets if ``set_ids`` is ``None``)."""
    ids = list(catalog.tasting_sets) if set_ids is None else list(set_ids)
    return [member for set_id in ids for member in catalog.resolve_set(set_id)]


def _count(
    members: Iterable[ResolvedMember],
    group: Callable[[ResolvedMember], tuple[str, str]],
) -> list[CountEntry]:
    counter: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for member in members:
        key, label = group(member)
        counter[key] += 1
        labels.setdefault(key, label)
    entries = [CountEntry(key, labels[key], count) for key, count in counter.items()]
    return sorted(entries, key=lambda e: (-e.count, e.label.casefold(), e.key))


def count_by_distillery(catalog: Catalog, set_ids: Iterable[str] | None = None) -> list[CountEntry]:
    """Bottles per distillery. Without an entry the free-text ``distillery_name`` is used."""

    def group(member: ResolvedMember) -> tuple[str, str]:
        if member.distillery is not None:
            return member.distillery.id, member.distillery.label
        name = member.spirit.distillery_name or UNKNOWN_KEY
        return f"name:{name.casefold()}", name

    return _count(selected_members(catalog, set_ids), group)


def count_by_category(
    catalog: Catalog, set_ids: Iterable[str] | None = None, lang: str = DEFAULT_LANGUAGE
) -> list[CountEntry]:
    """Bottles per kind of spirit; labels are localized with ``lang``."""
    from tastingsets.i18n import localized

    return _count(
        selected_members(catalog, set_ids),
        lambda m: (m.category.id, localized(m.category.names, lang)),
    )


def count_by_country(
    catalog: Catalog, set_ids: Iterable[str] | None = None, lang: str = DEFAULT_LANGUAGE
) -> list[CountEntry]:
    """Bottles per country. Members without distillery entry are grouped under ``unknown``."""
    from tastingsets.i18n import country_name

    def group(member: ResolvedMember) -> tuple[str, str]:
        if member.country is None:
            return UNKNOWN_KEY, UNKNOWN_KEY
        return member.country, country_name(member.country, lang)

    return _count(selected_members(catalog, set_ids), group)


def repeated_spirits(
    catalog: Catalog, set_ids: Iterable[str] | None = None
) -> list[RepeatedSpirit]:
    """Spirits occurring more than once, within one set or across several sets."""
    fqns: dict[str, list[str]] = {}
    sets: dict[str, list[str]] = {}
    spirits: dict[str, Spirit] = {}
    for member in selected_members(catalog, set_ids):
        spirits[member.spirit.id] = member.spirit
        fqns.setdefault(member.spirit.id, []).append(member.fqn)
        if member.set_id not in sets.setdefault(member.spirit.id, []):
            sets[member.spirit.id].append(member.set_id)
    result = [
        RepeatedSpirit(spirits[sid], len(places), tuple(places), tuple(sets[sid]))
        for sid, places in fqns.items()
        if len(places) > 1
    ]
    return sorted(result, key=lambda r: (-r.count, r.spirit.label.casefold(), r.spirit.id))


def abv_summary(catalog: Catalog, set_ids: Iterable[str] | None = None) -> AbvSummary | None:
    """Minimum, maximum and mean alcohol content over all bottles (``None`` if no bottles)."""
    values = [m.spirit.abv for m in selected_members(catalog, set_ids)]
    if not values:
        return None
    return AbvSummary(min(values), max(values), sum(values) / len(values))


def totals(catalog: Catalog, set_ids: Iterable[str] | None = None) -> Totals:
    """Number of sets, bottles and distinct spirits."""
    ids = list(catalog.tasting_sets) if set_ids is None else list(set_ids)
    members = selected_members(catalog, ids)
    return Totals(len(ids), len(members), len({m.spirit.id for m in members}))


@dataclass(frozen=True)
class StatsReport:
    """All statistics for a selection of sets, ready to be rendered."""

    totals: Totals
    by_distillery: list[CountEntry]
    by_category: list[CountEntry]
    by_country: list[CountEntry]
    repeated: list[RepeatedSpirit]
    abv: AbvSummary | None


def build_report(
    catalog: Catalog, set_ids: Iterable[str] | None = None, lang: str = DEFAULT_LANGUAGE
) -> StatsReport:
    """Compute every statistic for the selected sets (all sets if ``set_ids`` is ``None``)."""
    ids = list(catalog.tasting_sets) if set_ids is None else list(set_ids)
    return StatsReport(
        totals=totals(catalog, ids),
        by_distillery=count_by_distillery(catalog, ids),
        by_category=count_by_category(catalog, ids, lang),
        by_country=count_by_country(catalog, ids, lang),
        repeated=repeated_spirits(catalog, ids),
        abv=abv_summary(catalog, ids),
    )
