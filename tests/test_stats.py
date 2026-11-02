import pytest

from tastingsets import stats
from tastingsets.catalog import Catalog, UnknownReferenceError
from tastingsets.repository.json_repository import JsonRepository


@pytest.fixture
def catalog(data_dir):
    return Catalog.from_repository(JsonRepository(data_dir))


def as_tuples(entries):
    return [(e.key, e.label, e.count) for e in entries]


def test_count_by_distillery_all_sets(catalog):
    assert as_tuples(stats.count_by_distillery(catalog)) == [
        ("ardbeg", "Ardbeg", 3),
        ("nonino", "Nonino", 1),
        ("name:secret distillery", "Secret Distillery", 1),
    ]


def test_count_by_distillery_selected_set(catalog):
    result = stats.count_by_distillery(catalog, ["advent-2025"])
    assert as_tuples(result) == [
        ("ardbeg", "Ardbeg", 1),
        ("name:secret distillery", "Secret Distillery", 1),
    ]


def test_count_by_category(catalog):
    assert as_tuples(stats.count_by_category(catalog)) == [
        ("single-malt", "Single Malt", 4),
        ("grappa", "Grappa", 1),
    ]


def test_count_by_category_uses_language_with_fallback(catalog):
    labels = {e.key: e.label for e in stats.count_by_category(catalog, lang="en")}
    assert labels == {"single-malt": "Single Malt", "grappa": "Grappa"}  # grappa: fallback to de


def test_count_by_country_groups_unknown(catalog):
    assert as_tuples(stats.count_by_country(catalog, lang="de")) == [
        ("GB", "Vereinigtes Königreich", 3),
        ("IT", "Italien", 1),
        ("unknown", "unknown", 1),
    ]


def test_count_by_country_uses_exact_region_code(tmp_path):
    from conftest import DISTILLERIES, make_data_dir

    distilleries = [
        {**DISTILLERIES[0], "country": "GB-SCT", "region": "Islay"},
        {"_id": "nonino", "name": "Nonino", "country": "GB"},
    ]
    root = make_data_dir(tmp_path / "data", distilleries=distilleries)
    catalog = Catalog.from_repository(JsonRepository(root))
    assert as_tuples(stats.count_by_country(catalog, lang="de")) == [
        ("GB-SCT", "Schottland", 3),
        ("unknown", "unknown", 1),  # ties are sorted by label
        ("GB", "Vereinigtes Königreich", 1),
    ]


def _region_catalog(tmp_path, ardbeg, nonino):
    from conftest import DISTILLERIES, make_data_dir

    distilleries = [
        {**DISTILLERIES[0], **ardbeg},
        {**DISTILLERIES[1], **nonino},
    ]
    root = make_data_dir(tmp_path / "data", distilleries=distilleries)
    return Catalog.from_repository(JsonRepository(root))


def test_count_by_region_across_countries(catalog):
    assert as_tuples(stats.count_by_region(catalog, lang="de")) == [
        ("country:GB", "Vereinigtes Königreich, –", 3),
        ("country:IT", "Italien, –", 1),
        ("unknown", "unknown", 1),
    ]


def test_count_by_region_empty_without_members_from_country(catalog):
    assert stats.count_by_region(catalog, country=stats.SCOTLAND) == []
    assert stats.count_by_region(catalog, []) == []


def test_count_by_region_ignores_case(tmp_path):
    catalog = _region_catalog(
        tmp_path,
        {"country": "GB-SCT", "region": "Islay"},
        {"country": "GB-SCT", "region": "ISLAY"},
    )
    result = stats.count_by_region(catalog, country=stats.SCOTLAND)
    assert as_tuples(result) == [("region:GB-SCT:islay", "Islay", 4)]


def test_count_by_region_filters_by_exact_country(tmp_path):
    catalog = _region_catalog(
        tmp_path,
        {"country": "GB-SCT", "region": "Islay"},
        {"country": "IT", "region": "Friuli"},
    )
    assert as_tuples(stats.count_by_region(catalog, country=stats.SCOTLAND)) == [
        ("region:GB-SCT:islay", "Islay", 3)
    ]
    assert as_tuples(stats.count_by_region(catalog, ["advent-2025"], stats.SCOTLAND)) == [
        ("region:GB-SCT:islay", "Islay", 1)
    ]
    assert as_tuples(stats.count_by_region(catalog, country="IT")) == [
        ("region:IT:friuli", "Friuli", 1)
    ]
    assert stats.count_by_region(catalog, country="GB") == []
    assert as_tuples(stats.count_by_region(catalog, lang="de")) == [
        ("region:GB-SCT:islay", "Schottland, Islay", 3),
        ("region:IT:friuli", "Italien, Friuli", 1),
        ("unknown", "unknown", 1),
    ]


def test_count_by_region_separates_same_region_in_different_countries(tmp_path):
    catalog = _region_catalog(
        tmp_path,
        {"country": "GB-SCT", "region": "Highland"},
        {"country": "US", "region": "highland"},
    )
    assert as_tuples(stats.count_by_region(catalog, lang="de")) == [
        ("region:GB-SCT:highland", "Schottland, Highland", 3),
        ("unknown", "unknown", 1),  # ties are sorted by label
        ("region:US:highland", "Vereinigte Staaten, highland", 1),
    ]
    labels = {e.key: e.label for e in stats.count_by_region(catalog, lang="en")}
    assert labels == {
        "region:GB-SCT:highland": "Scotland, Highland",
        "region:US:highland": "United States, highland",
        "unknown": "unknown",
    }


def test_count_by_region_without_region_is_unknown(tmp_path):
    catalog = _region_catalog(
        tmp_path,
        {"country": "GB-SCT"},
        {"country": "GB-SCT", "region": "Unknown"},
    )
    result = stats.count_by_region(catalog, country=stats.SCOTLAND)
    assert as_tuples(result) == [
        ("unknown", "unknown", 3),
        ("region:GB-SCT:unknown", "Unknown", 1),
    ]


def test_build_report_region_countries(catalog, monkeypatch):
    report = stats.build_report(catalog, region_countries=[None, "IT"])
    assert report.by_region == [
        stats.RegionStats(
            None,
            [
                stats.CountEntry("country:GB", "Vereinigtes Königreich, –", 3),
                stats.CountEntry("country:IT", "Italien, –", 1),
                stats.CountEntry("unknown", "unknown", 1),
            ],
        ),
        stats.RegionStats("IT", [stats.CountEntry("unknown", "unknown", 1)]),
    ]
    english = stats.build_report(catalog, lang="en", region_countries=[None])
    assert english.by_region[0].entries[0].label.startswith("United Kingdom, ")

    monkeypatch.setattr(stats, "REGION_STATS_COUNTRIES", ("IT",))
    assert stats.build_report(catalog).by_region == [
        stats.RegionStats("IT", [stats.CountEntry("unknown", "unknown", 1)])
    ]


def test_repeated_spirits_across_and_within_sets(catalog):
    (repeated,) = stats.repeated_spirits(catalog)
    assert repeated.spirit.id == "ardbeg-10"
    assert repeated.count == 3
    assert repeated.fqns == ("advent-2025/1", "advent-2026/2", "advent-2026/3")
    assert repeated.set_ids == ("advent-2025", "advent-2026")


def test_repeated_spirits_respects_selection(catalog):
    assert stats.repeated_spirits(catalog, ["advent-2025"]) == []
    (within,) = stats.repeated_spirits(catalog, ["advent-2026"])
    assert within.count == 2 and within.set_ids == ("advent-2026",)


def test_abv_summary(catalog):
    summary = stats.abv_summary(catalog, ["advent-2025"])
    assert (summary.minimum, summary.maximum) == (46.0, 48.2)
    assert summary.mean == pytest.approx(47.1)


def test_abv_summary_empty_selection(catalog):
    assert stats.abv_summary(catalog, []) is None


def test_totals(catalog):
    assert stats.totals(catalog) == stats.Totals(sets=2, members=5, distinct_spirits=3)
    assert stats.totals(catalog, ["advent-2026"]) == stats.Totals(1, 3, 2)


def test_build_report_bundles_all_statistics(catalog):
    report = stats.build_report(catalog, ["advent-2026"], lang="en")
    assert report.totals == stats.Totals(1, 3, 2)
    assert as_tuples(report.by_country) == [("GB", "United Kingdom", 2), ("IT", "Italy", 1)]
    assert [r.spirit.id for r in report.repeated] == ["ardbeg-10"]
    assert report.abv is not None
    assert [e.key for e in report.by_category] == ["single-malt", "grappa"]
    assert [e.key for e in report.by_distillery] == ["ardbeg", "nonino"]
    assert report.by_region == [stats.RegionStats(stats.SCOTLAND, [])]


def test_unknown_set_in_selection_raises(catalog):
    with pytest.raises(UnknownReferenceError):
        stats.selected_members(catalog, ["nope"])
