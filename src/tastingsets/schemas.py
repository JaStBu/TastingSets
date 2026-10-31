"""JSON Schema generation for the data files (editor support and documentation)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from tastingsets.repository.base import COLLECTIONS

SCHEMA_SUFFIX = ".schema.json"


def generate_schemas() -> dict[str, dict]:
    """JSON Schema per collection; a data file holds one document or a list of documents."""
    schemas = {}
    for collection, model in COLLECTIONS.items():
        schema = TypeAdapter(model | list[model]).json_schema(by_alias=True)
        schemas[collection] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"{collection} file",
            **schema,
        }
    return schemas


def render_schema(schema: dict) -> str:
    """Deterministic text representation used for writing and comparing schema files."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def write_schemas(out_dir: Path | str) -> list[Path]:
    """Write ``<collection>.schema.json`` files and return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for collection, schema in generate_schemas().items():
        path = out / f"{collection}{SCHEMA_SUFFIX}"
        path.write_text(render_schema(schema), encoding="utf-8")
        written.append(path)
    return written
