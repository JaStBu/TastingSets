"""Shared test helpers: build small data directories in ``tmp_path``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CATEGORIES = [
    {"_id": "single-malt", "names": {"de": "Single Malt", "en": "Single Malt"}},
    {"_id": "grappa", "names": {"de": "Grappa"}},
]
DISTILLERIES = [
    {"_id": "ardbeg", "name": "Ardbeg", "country": "GB"},
    {"_id": "nonino", "name": "Nonino", "country": "IT"},
]
SPIRITS = [
    {
        "_id": "ardbeg-10",
        "name": "Ardbeg 10",
        "category_id": "single-malt",
        "distillery_id": "ardbeg",
        "abv": 46.0,
    },
    {
        "_id": "nonino-grappa",
        "name": "Nonino Grappa",
        "category_id": "grappa",
        "distillery_id": "nonino",
        "abv": 41.0,
    },
    {
        "_id": "secret-12",
        "name": "Secret 12",
        "category_id": "single-malt",
        "distillery_name": "Secret Distillery",
        "abv": 48.2,
        "url": "https://example.org/secret",
    },
]
TASTING_SETS = [
    {
        "_id": "advent-2025",
        "name": "Advent 2025",
        "year": 2025,
        "members": [
            {"member_id": "1", "spirit_id": "ardbeg-10"},
            {"member_id": "2", "spirit_id": "secret-12", "notes": "cask strength"},
        ],
    },
    {
        "_id": "advent-2026",
        "name": "Advent 2026",
        "year": 2026,
        "members": [
            {"member_id": "1", "spirit_id": "nonino-grappa"},
            {"member_id": "2", "spirit_id": "ardbeg-10"},
            {"member_id": "3", "spirit_id": "ardbeg-10"},
        ],
    },
]


def write_json(path: Path, content) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def make_data_dir(root: Path, **overrides) -> Path:
    """Write a valid data directory; ``overrides`` replace a collection's content."""
    collections = {
        "categories": CATEGORIES,
        "distilleries": DISTILLERIES,
        "spirits": SPIRITS,
        "tasting_sets": TASTING_SETS,
    }
    collections.update(overrides)
    for name, content in collections.items():
        write_json(root / name / f"{name}.json", content)
    return root


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return make_data_dir(tmp_path / "data")
