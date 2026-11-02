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

#: Key used for members whose country or region is not known.
UNKNOWN_KEY = "unknown"
#: ISO 3166-2 code of Scotland.
SCOTLAND = "GB-SCT"
#: Countries (exact codes) that get a region table in reports; ``None`` means all countries.
REGION_STATS_COUNTRIES: tuple[str | None, ...] = (SCOTLAND,)
#: Shown instead of the region in cross-country labels when a distillery has no region.
MISSING_REGION = "–"


@dataclass(frozen=True)
class CountEntry:
    """``key`` identifies the group (an ``_id`` or ``unknown``), ``label`` is its display text."""

    key: str
    label: str
    count: int


@dataclass(frozen=True)
class RegionStats:
    """Bottles per region within one country (exact code) or across all countries (``None``)."""

    country: str | None
    entries: list[CountEntry]


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
    """Bottles per exact country code (``GB`` and ``GB-SCT`` are separate entries).

    Members without distillery entry are grouped under ``unknown``.
    """
    from tastingsets.i18n import country_name

    def group(member: ResolvedMember) -> tuple[str, str]:
        if member.country is None:
            return UNKNOWN_KEY, UNKNOWN_KEY
        return member.country, country_name(member.country, lang)

    return _count(selected_members(catalog, set_ids), group)


def count_by_region(
    catalog: Catalog,
    set_ids: Iterable[str] | None = None,
    country: str | None = None,
    lang: str = DEFAULT_LANGUAGE,
) -> list[CountEntry]:
    """Bottles per free-text ``region`` of the distillery; a region always belongs to its country.

    ``country`` restricts the count to one exact country code (``GB-SCT`` is not ``GB``). Bottles
    from other countries and bottles without distillery entry are then not counted, and the label
    is just the region. With ``None`` all bottles are counted across countries and the label is
    ``<country name>, <region>``, with the country name localized with ``lang``.

    Regions are compared case-insensitively; the label uses the first spelling found. A missing
    region is grouped under ``unknown`` (one country) or shown as ``<country name>, –`` (across
    countries); across countries, bottles without distillery entry count as ``unknown``.
    Returns an empty list if no bottle matches.
    """
    from tastingsets.i18n import country_name

    members = selected_members(catalog, set_ids)
    if country is not None:
        members = [m for m in members if m.country == country]

    def group(member: ResolvedMember) -> tuple[str, str]:
        if member.country is None:
            return UNKNOWN_KEY, UNKNOWN_KEY
        if member.region is None:
            if country is not None:
                return UNKNOWN_KEY, UNKNOWN_KEY
            return (
                f"country:{member.country}",
                f"{country_name(member.country, lang)}, {MISSING_REGION}",
            )
        key = f"region:{member.country}:{member.region.casefold()}"
        if country is not None:
            return key, member.region
        return key, f"{country_name(member.country, lang)}, {member.region}"

    return _count(members, group)


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
    by_region: list[RegionStats]
    repeated: list[RepeatedSpirit]
    abv: AbvSummary | None


def build_report(
    catalog: Catalog,
    set_ids: Iterable[str] | None = None,
    lang: str = DEFAULT_LANGUAGE,
    region_countries: Iterable[str | None] | None = None,
) -> StatsReport:
    """Compute every statistic for the selected sets (all sets if ``set_ids`` is ``None``).

    ``region_countries`` lists the countries (exact codes, ``None`` = across countries) that get
    a region statistic, in that order. If ``None``, ``REGION_STATS_COUNTRIES`` is used as it is
    when this function is called.
    """
    ids = list(catalog.tasting_sets) if set_ids is None else list(set_ids)
    countries = REGION_STATS_COUNTRIES if region_countries is None else region_countries
    return StatsReport(
        totals=totals(catalog, ids),
        by_distillery=count_by_distillery(catalog, ids),
        by_category=count_by_category(catalog, ids, lang),
        by_country=count_by_country(catalog, ids, lang),
        by_region=[RegionStats(c, count_by_region(catalog, ids, c, lang)) for c in countries],
        repeated=repeated_spirits(catalog, ids),
        abv=abv_summary(catalog, ids),
    )
