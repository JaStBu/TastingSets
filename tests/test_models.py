import pytest
from pydantic import ValidationError

from tastingsets.models import Category, Distillery, SetMember, Spirit, TastingSet


def spirit(**overrides):
    data = {
        "_id": "ardbeg-10",
        "name": "Ardbeg 10",
        "category_id": "single-malt",
        "abv": 46.0,
        "distillery_id": "ardbeg",
    }
    data.update(overrides)
    return data


def test_category_requires_german_name():
    assert Category.model_validate({"_id": "grappa", "names": {"de": "Grappa"}}).id == "grappa"
    with pytest.raises(ValidationError):
        Category.model_validate({"_id": "grappa", "names": {"en": "Grappa"}})


def test_distillery_country_validation():
    d = Distillery.model_validate({"_id": "ardbeg", "name": "Ardbeg", "country": "GB"})
    assert d.country == "GB"
    for bad in ("gb", "XX1", "Scotland", "ZZZ"):
        with pytest.raises(ValidationError):
            Distillery.model_validate({"_id": "ardbeg", "name": "Ardbeg", "country": bad})


@pytest.mark.parametrize("bad_id", ["Ardbeg", "ardbeg_10", "-a", "a--b", "", "a b"])
def test_slug_validation(bad_id):
    with pytest.raises(ValidationError):
        Spirit.model_validate(spirit(_id=bad_id))


@pytest.mark.parametrize("abv", [0, -1, 100.5])
def test_abv_out_of_range(abv):
    with pytest.raises(ValidationError):
        Spirit.model_validate(spirit(abv=abv))


def test_url_must_be_http():
    assert Spirit.model_validate(spirit(url="https://example.org/x")).url is not None
    with pytest.raises(ValidationError):
        Spirit.model_validate(spirit(url="not a url"))


def test_spirit_needs_distillery_id_or_name():
    no_ref = spirit()
    del no_ref["distillery_id"]
    with pytest.raises(ValidationError):
        Spirit.model_validate(no_ref)
    assert Spirit.model_validate({**no_ref, "distillery_name": "Unknown"}).distillery_id is None


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        Spirit.model_validate(spirit(abc=1))


def test_label_prefers_display_name():
    assert Spirit.model_validate(spirit()).label == "Ardbeg 10"
    assert Spirit.model_validate(spirit(display_name="Ten")).label == "Ten"


def test_dump_uses_underscore_id():
    dumped = Spirit.model_validate(spirit()).model_dump(exclude_none=True)
    assert dumped["_id"] == "ardbeg-10"
    assert "id" not in dumped


def test_set_member_id_is_string_and_validated():
    assert SetMember(member_id="24", spirit_id="a").member_id == "24"
    with pytest.raises(ValidationError):
        SetMember.model_validate({"member_id": 1, "spirit_id": "a"})
    with pytest.raises(ValidationError):
        SetMember.model_validate({"member_id": "a b", "spirit_id": "a"})


def test_tasting_set_rejects_duplicate_member_ids():
    base = {"_id": "advent", "names": {"de": "Advent"}}
    members = [{"member_id": "1", "spirit_id": "a"}, {"member_id": "1", "spirit_id": "b"}]
    with pytest.raises(ValidationError):
        TastingSet.model_validate({**base, "members": members})


def test_tasting_set_fqn_and_order():
    ts = TastingSet.model_validate(
        {
            "_id": "advent-2026",
            "names": {"de": "Advent"},
            "members": [{"member_id": "2", "spirit_id": "a"}, {"member_id": "1", "spirit_id": "b"}],
        }
    )
    assert [ts.fqn(m) for m in ts.members] == ["advent-2026/2", "advent-2026/1"]


def test_tasting_set_name_is_localized():
    ts = TastingSet.model_validate(
        {
            "_id": "advent",
            "names": {"de": "Adventskalender", "en": "Advent calendar"},
            "members": [],
        }
    )
    assert ts.names["en"] == "Advent calendar"
    with pytest.raises(ValidationError):
        TastingSet.model_validate(
            {"_id": "advent", "names": {"en": "Advent calendar"}, "members": []}
        )


def test_set_member_notes_are_localized():
    member = SetMember.model_validate(
        {"member_id": "1", "spirit_id": "a", "notes": {"de": "Fassstärke", "en": "Cask strength"}}
    )
    assert member.notes == {"de": "Fassstärke", "en": "Cask strength"}
    with pytest.raises(ValidationError):
        SetMember.model_validate(
            {"member_id": "1", "spirit_id": "a", "notes": {"en": "only english"}}
        )
