import pytest

from conftest import SPIRITS, make_data_dir, write_json
from tastingsets.repository.json_repository import JsonRepository


def test_loads_all_collections(data_dir):
    repo = JsonRepository(data_dir)
    assert repo.load_errors == []
    assert len(repo.categories()) == 2
    assert len(repo.distilleries()) == 2
    assert len(repo.spirits()) == 3
    assert [t.id for t in repo.tasting_sets()] == ["advent-2025", "advent-2026"]


def test_missing_data_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        JsonRepository(tmp_path / "nope")


def test_missing_collection_folder_is_empty(tmp_path):
    (tmp_path / "data").mkdir()
    repo = JsonRepository(tmp_path / "data")
    assert repo.spirits() == []
    assert repo.load_errors == []


def test_single_object_and_multiple_files(tmp_path):
    root = make_data_dir(tmp_path / "data", spirits=[])
    write_json(root / "spirits" / "a.json", SPIRITS[0])  # single object
    write_json(root / "spirits" / "b.json", SPIRITS[1:])  # list
    repo = JsonRepository(root)
    assert repo.load_errors == []
    assert [s.id for s in repo.spirits()] == ["ardbeg-10", "nonino-grappa", "secret-12"]


def test_duplicate_id_across_files(tmp_path):
    root = make_data_dir(tmp_path / "data")
    write_json(root / "spirits" / "zzz.json", [SPIRITS[0]])
    repo = JsonRepository(root)
    errors = [e for e in repo.load_errors if e.code == "DUPLICATE_ID"]
    assert len(errors) == 1
    assert errors[0].file.endswith("zzz.json")
    assert errors[0].object_id == "ardbeg-10"
    assert len(repo.spirits()) == 3


def test_schema_error_contains_file_and_is_skipped(tmp_path):
    bad = {**SPIRITS[0], "_id": "bad-one", "abv": 500}
    root = make_data_dir(tmp_path / "data", spirits=[SPIRITS[1], bad])
    repo = JsonRepository(root)
    assert [s.id for s in repo.spirits()] == ["nonino-grappa"]
    (error,) = repo.load_errors
    assert error.code == "SCHEMA"
    assert error.object_id == "bad-one"
    assert error.file.endswith("spirits.json")
    assert "abv" in error.message


def test_invalid_json_is_reported(tmp_path):
    root = make_data_dir(tmp_path / "data")
    (root / "spirits" / "broken.json").write_text("{not json", encoding="utf-8")
    repo = JsonRepository(root)
    assert [e.code for e in repo.load_errors] == ["INVALID_JSON"]


def test_duplicate_member_id_has_own_code(tmp_path):
    ts = {
        "_id": "dup",
        "name": "Dup",
        "members": [{"member_id": "1", "spirit_id": "a"}, {"member_id": "1", "spirit_id": "b"}],
    }
    repo = JsonRepository(make_data_dir(tmp_path / "data", tasting_sets=[ts]))
    assert [e.code for e in repo.load_errors] == ["DUPLICATE_MEMBER_ID"]


def test_source_of(data_dir):
    repo = JsonRepository(data_dir)
    assert repo.source_of("spirits", "ardbeg-10").endswith("spirits.json")
    assert repo.source_of("spirits", "unknown") is None
