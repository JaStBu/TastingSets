from pathlib import Path

from tastingsets.repository.json_repository import JsonRepository
from tastingsets.validation import Severity, validate

DATA_DIR = Path(__file__).parents[1] / "data"


def test_real_data_has_no_errors():
    issues = validate(JsonRepository(DATA_DIR))
    errors = [i for i in issues if i.severity is Severity.ERROR]
    assert errors == [], errors


def test_real_data_warns_only_about_known_missing_distillery():
    issues = validate(JsonRepository(DATA_DIR))
    assert [(i.code, i.object_id) for i in issues] == [
        ("MISSING_DISTILLERY_ENTRY", "johnnie-walker-black-label")
    ]
