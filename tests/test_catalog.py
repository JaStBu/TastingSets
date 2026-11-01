import pytest

from tastingsets.catalog import Catalog, UnknownReferenceError
from tastingsets.repository.json_repository import JsonRepository


@pytest.fixture
def catalog(data_dir):
    return Catalog.from_repository(JsonRepository(data_dir))


def test_from_repository_indexes_by_id(catalog):
    assert set(catalog.spirits) == {"ardbeg-10", "nonino-grappa", "secret-12"}
    assert list(catalog.tasting_sets) == ["advent-2025", "advent-2026"]


def test_resolve_set_with_distillery_entry(catalog):
    first, _ = catalog.resolve_set("advent-2025")
    assert first.fqn == "advent-2025/1"
    assert first.distillery_label == "Ardbeg"
    assert first.country == "GB"
    assert first.category.id == "single-malt"


def test_resolve_member_without_distillery_entry(catalog):
    member = catalog.resolve_member("advent-2025/2")
    assert member.distillery is None
    assert member.distillery_label == "Secret Distillery"
    assert member.country is None
    assert member.notes == {"de": "cask strength"}


def test_same_member_id_in_different_sets_is_distinguished(catalog):
    assert catalog.resolve_member("advent-2025/1").spirit.id == "ardbeg-10"
    assert catalog.resolve_member("advent-2026/1").spirit.id == "nonino-grappa"


@pytest.mark.parametrize("fqn", ["advent-2025/99", "nope/1", "advent-2025", ""])
def test_unknown_member_raises(catalog, fqn):
    with pytest.raises(UnknownReferenceError):
        catalog.resolve_member(fqn)


def test_unknown_set_raises(catalog):
    with pytest.raises(UnknownReferenceError):
        catalog.resolve_set("nope")
