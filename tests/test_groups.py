"""Tests for the optional sub-groups of tasting sets (models, loading, catalog, stats, site)."""

import pytest
from pydantic import ValidationError

from conftest import GROUPED_SET, TASTING_SETS, flat_version, make_data_dir
from tastingsets import stats
from tastingsets.catalog import Catalog
from tastingsets.models import SetGroup, TastingSet
from tastingsets.repository.json_repository import JsonRepository
from tastingsets.site.builder import build, uniform_group_size
from tastingsets.validation import validate


def member(member_id: str, spirit_id: str = "ardbeg-10") -> dict:
    return {"member_id": member_id, "spirit_id": spirit_id}


def group(group_id: str, members: list[dict], **extra) -> dict:
    return {"group_id": group_id, "names": {"de": group_id.title()}, "members": members, **extra}


def tasting_set(**fields) -> dict:
    return {"_id": "ts", "name": "TS", **fields}


@pytest.fixture
def grouped_dir(tmp_path):
    return make_data_dir(tmp_path / "data", tasting_sets=[*TASTING_SETS, GROUPED_SET])


@pytest.fixture
def catalog(grouped_dir):
    return Catalog.from_repository(JsonRepository(grouped_dir))


# -- models ------------------------------------------------------------------------------------


def test_grouped_set_is_valid_and_keeps_order():
    ts = TastingSet.model_validate(GROUPED_SET)
    assert ts.is_grouped
    assert [g.group_id for g in ts.groups] == ["wine-finish", "grappa-round"]
    assert [m.member_id for m in ts.all_members] == ["1", "2", "3", "4"]


def test_flat_set_is_not_grouped():
    ts = TastingSet.model_validate(flat_version(GROUPED_SET))
    assert not ts.is_grouped
    assert [m.member_id for m in ts.all_members] == ["1", "2", "3", "4"]
    assert ts.group_of("1") is None


def test_group_of_finds_group():
    ts = TastingSet.model_validate(GROUPED_SET)
    assert ts.group_of("2").group_id == "wine-finish"
    assert ts.group_of("4").group_id == "grappa-round"
    assert ts.group_of("99") is None


def test_fqn_does_not_contain_group():
    ts = TastingSet.model_validate(GROUPED_SET)
    assert ts.fqn(ts.all_members[3]) == "grouped-2026/4"


@pytest.mark.parametrize(
    "fields",
    [
        {},  # neither members nor groups
        {"members": [member("1")], "groups": [group("a", [member("2")])]},  # both
        {"groups": []},
        {"members": []} | {"groups": []},
        {"groups": [group("a", [])]},  # group without members
    ],
)
def test_invalid_structures_are_rejected(fields):
    with pytest.raises(ValidationError):
        TastingSet.model_validate(tasting_set(**fields))


def test_empty_flat_members_list_is_still_a_flat_set():
    assert not TastingSet.model_validate(tasting_set(members=[])).is_grouped


def test_group_requires_german_name_and_valid_slug():
    with pytest.raises(ValidationError):
        SetGroup.model_validate(group("a", [member("1")], names={"en": "A"}))
    with pytest.raises(ValidationError):
        SetGroup.model_validate(group("Not A Slug", [member("1")]))
    with pytest.raises(ValidationError):
        SetGroup.model_validate(group("a", [member("1")], description={"en": "only english"}))


def test_unknown_group_field_is_rejected():
    with pytest.raises(ValidationError):
        SetGroup.model_validate(group("a", [member("1")], color="red"))


def test_duplicate_group_id_is_rejected():
    groups = [group("a", [member("1")]), group("a", [member("2")])]
    with pytest.raises(ValidationError, match="duplicate group_id"):
        TastingSet.model_validate(tasting_set(groups=groups))


def test_member_id_must_be_unique_across_groups():
    groups = [group("a", [member("1")]), group("b", [member("1")])]
    with pytest.raises(ValidationError, match="duplicate member_id"):
        TastingSet.model_validate(tasting_set(groups=groups))


def test_dump_roundtrip_keeps_groups():
    ts = TastingSet.model_validate(GROUPED_SET)
    assert TastingSet.model_validate(ts.model_dump(exclude_none=True)) == ts
    assert ts.model_dump(exclude_none=True)["_id"] == "grouped-2026"


# -- loading and validation --------------------------------------------------------------------


def test_repository_reports_group_errors_with_own_codes(tmp_path):
    sets = [
        tasting_set(_id="dup-group", groups=[group("a", [member("1")]), group("a", [member("2")])]),
        tasting_set(
            _id="dup-member", groups=[group("a", [member("1")]), group("b", [member("1")])]
        ),
        tasting_set(_id="both", members=[member("1")], groups=[group("a", [member("2")])]),
    ]
    repo = JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=sets))
    assert [(e.code, e.object_id) for e in repo.load_errors] == [
        ("DUPLICATE_GROUP_ID", "dup-group"),
        ("DUPLICATE_MEMBER_ID", "dup-member"),
        ("SCHEMA", "both"),
    ]


def test_valid_grouped_set_adds_no_issues(grouped_dir):
    issues = validate(JsonRepository(grouped_dir))
    assert [i.code for i in issues] == ["MISSING_DISTILLERY_ENTRY"]


def test_unknown_spirit_inside_group_is_reported(tmp_path):
    ts = tasting_set(groups=[group("a", [member("1", "ghost")])])
    issues = validate(JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts])))
    assert "UNKNOWN_SPIRIT" in [i.code for i in issues]


def test_spirits_used_only_in_groups_are_not_unused(tmp_path):
    ts = tasting_set(groups=[group("a", [member("1", "ardbeg-10"), member("2", "secret-12")])])
    issues = validate(JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts])))
    unused = {i.object_id for i in issues if i.code == "UNUSED_SPIRIT"}
    assert unused == {"nonino-grappa"}


# -- catalog -----------------------------------------------------------------------------------


def test_resolve_groups_for_grouped_set(catalog):
    groups = catalog.resolve_groups("grouped-2026")
    assert [g.group.group_id for g in groups] == ["wine-finish", "grappa-round"]
    assert [[m.member_id for m in g.members] for g in groups] == [["1", "2"], ["3", "4"]]
    assert {m.group_id for m in groups[0].members} == {"wine-finish"}


def test_resolve_groups_for_flat_set_returns_single_unnamed_group(catalog):
    (only,) = catalog.resolve_groups("advent-2025")
    assert only.group is None
    assert [m.fqn for m in only.members] == ["advent-2025/1", "advent-2025/2"]
    assert {m.group_id for m in only.members} == {None}


def test_resolve_set_is_flat_for_grouped_set(catalog):
    assert [m.fqn for m in catalog.resolve_set("grouped-2026")] == [
        "grouped-2026/1",
        "grouped-2026/2",
        "grouped-2026/3",
        "grouped-2026/4",
    ]


def test_resolve_member_in_group(catalog):
    resolved = catalog.resolve_member("grouped-2026/3")
    assert resolved.spirit.id == "nonino-grappa"
    assert resolved.group_id == "grappa-round"


# -- statistics are not affected by groups -----------------------------------------------------


def test_stats_are_identical_for_grouped_and_flat_set(tmp_path):
    grouped = Catalog.from_repository(
        JsonRepository(make_data_dir(tmp_path / "a", tasting_sets=[GROUPED_SET]))
    )
    flat = Catalog.from_repository(
        JsonRepository(make_data_dir(tmp_path / "b", tasting_sets=[flat_version(GROUPED_SET)]))
    )
    assert stats.build_report(grouped) == stats.build_report(flat)
    assert stats.build_report(grouped).totals == stats.Totals(1, 4, 3)


# -- site --------------------------------------------------------------------------------------


def read_set_page(out, set_id, lang="de"):
    return (out / lang / "sets" / set_id / "index.html").read_text(encoding="utf-8")


def test_uniform_group_size():
    equal = TastingSet.model_validate(GROUPED_SET)
    unequal = TastingSet.model_validate(
        tasting_set(groups=[group("a", [member("1")]), group("b", [member("2"), member("3")])])
    )
    flat = TastingSet.model_validate(flat_version(GROUPED_SET))
    assert uniform_group_size(equal) == 2
    assert uniform_group_size(unequal) is None
    assert uniform_group_size(flat) is None


def test_set_page_shows_groups_in_order(grouped_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(grouped_dir), out)
    html = read_set_page(out, "grouped-2026")
    assert html.count('class="group-header"') == 2
    assert 'id="group-wine-finish"' in html and 'id="group-grappa-round"' in html
    assert html.index("Weinfinish") < html.index("Grappa-Runde")
    assert "Gereift in Weinfässern" in html
    assert "Dieses Set besteht aus 2 Gruppen à 2 Flaschen." in html
    # members appear below their group header
    assert html.index("Weinfinish") < html.index('id="member-1"') < html.index("Grappa-Runde")
    assert html.index("Grappa-Runde") < html.index('id="member-3"')


def test_set_page_without_groups_has_no_group_elements(grouped_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(grouped_dir), out)
    html = read_set_page(out, "advent-2025")
    assert "group-header" not in html
    assert "Dieses Set besteht aus" not in html
    members_table = html.split("</table>")[0]  # the statistics below also contain tables
    assert members_table.count("<tbody") == 1


def test_unequal_groups_have_no_size_in_text(tmp_path):
    ts = tasting_set(groups=[group("a", [member("1")]), group("b", [member("2"), member("3")])])
    out = tmp_path / "dist"
    build(JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts])), out)
    html = read_set_page(out, "ts")
    assert "Dieses Set besteht aus 2 Gruppen." in html
    assert "à" not in html


def test_single_group_uses_singular(tmp_path):
    ts = tasting_set(groups=[group("a", [member("1"), member("2")])])
    out = tmp_path / "dist"
    build(JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts])), out)
    assert "Dieses Set besteht aus 1 Gruppe mit 2 Flaschen." in read_set_page(out, "ts")


def test_group_texts_are_localized_with_fallback(grouped_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(grouped_dir), out, languages=["de", "en"])
    html = read_set_page(out, "grouped-2026", lang="en")
    assert "Wine finish" in html
    assert "Matured in wine casks" in html
    assert "Grappa-Runde" in html  # no English name -> German fallback
    assert "This set consists of 2 groups of 2 bottles each." in html


def test_group_texts_are_escaped(tmp_path):
    ts = tasting_set(groups=[group("a", [member("1")], names={"de": "<script>x</script>"})])
    out = tmp_path / "dist"
    build(JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts])), out)
    html = read_set_page(out, "ts")
    assert "<script>x" not in html
    assert "&lt;script&gt;" in html


def test_index_page_shows_group_count(grouped_dir, tmp_path):
    out = tmp_path / "dist"
    build(JsonRepository(grouped_dir), out)
    html = (out / "de" / "index.html").read_text(encoding="utf-8")
    assert "· 2 Gruppen" in html
    # the flat sets do not mention groups
    flat_entry = html.split("advent-2025/")[1].split("</li>")[0]
    assert "Gruppe" not in flat_entry
