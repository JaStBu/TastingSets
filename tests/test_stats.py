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


def test_unknown_set_in_selection_raises(catalog):
    with pytest.raises(UnknownReferenceError):
        stats.selected_members(catalog, ["nope"])
