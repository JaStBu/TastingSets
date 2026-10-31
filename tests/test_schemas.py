import json
from pathlib import Path

from tastingsets.cli import main
from tastingsets.repository.base import COLLECTIONS
from tastingsets.schemas import generate_schemas, render_schema, write_schemas

REPO_ROOT = Path(__file__).parents[1]


def test_generate_schemas_covers_all_collections_and_uses_aliases():
    schemas = generate_schemas()
    assert set(schemas) == set(COLLECTIONS)
    assert '"_id"' in render_schema(schemas["spirits"])


def test_write_schemas(tmp_path):
    paths = write_schemas(tmp_path / "schemas")
    assert sorted(p.name for p in paths) == sorted(f"{c}.schema.json" for c in COLLECTIONS)
    assert json.loads(paths[0].read_text(encoding="utf-8"))["$schema"]


def test_cli_schema(tmp_path, capsys):
    assert main(["schema", "--out", str(tmp_path / "s")]) == 0
    assert (tmp_path / "s" / "spirits.schema.json").is_file()
    assert "wrote 4 schema(s)" in capsys.readouterr().out


def test_committed_schemas_are_up_to_date():
    for collection, schema in generate_schemas().items():
        committed = (REPO_ROOT / "schemas" / f"{collection}.schema.json").read_text(
            encoding="utf-8"
        )
        assert committed == render_schema(schema), (
            f"schemas/{collection}.schema.json is outdated; run `uv run tastingsets schema`"
        )
