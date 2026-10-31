from pathlib import Path

from tastingsets.repository.json_repository import JsonRepository
from tastingsets.validation import Severity, has_errors, validate

FIXTURES = Path(__file__).parent / "fixtures" / "data"


def codes(issues, severity=None):
    return sorted(i.code for i in issues if severity is None or i.severity is severity)


def test_valid_data_only_warns_about_missing_distillery_entry(data_dir):
    issues = validate(JsonRepository(data_dir))
    assert codes(issues) == ["MISSING_DISTILLERY_ENTRY"]
    assert issues[0].object_id == "secret-12"
    assert issues[0].file.endswith("spirits.json")
    assert not has_errors(issues)


def test_every_issue_code_is_reported_for_fixture_data():
    issues = validate(JsonRepository(FIXTURES))
    assert codes(issues, Severity.ERROR) == [
        "DUPLICATE_ID",
        "DUPLICATE_MEMBER_ID",
        "INVALID_JSON",
        "SCHEMA",
        "UNKNOWN_CATEGORY",
        "UNKNOWN_DISTILLERY",
        "UNKNOWN_SPIRIT",
    ]
    assert codes(issues, Severity.WARNING) == [
        "DISTILLERY_NAME_MATCHES_ENTRY",
        "MISSING_DISTILLERY_ENTRY",
        "UNUSED_SPIRIT",
    ]
    assert has_errors(issues)


def test_has_errors_false_for_empty_list():
    assert has_errors([]) is False
