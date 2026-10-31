from pathlib import Path

from tastingsets.cli import format_issue, github_annotation, main
from tastingsets.validation import Issue, Severity

FIXTURES = Path(__file__).parent / "fixtures" / "data"


def test_main_without_command_prints_help(capsys):
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_validate_warnings_only_exits_zero(data_dir, capsys):
    assert main(["validate", "--data", str(data_dir)]) == 0
    out = capsys.readouterr().out
    assert "MISSING_DISTILLERY_ENTRY" in out
    assert "0 error(s), 1 warning(s)" in out


def test_validate_strict_fails_on_warnings(data_dir):
    assert main(["validate", "--data", str(data_dir), "--strict"]) == 1


def test_validate_errors_exit_one(capsys):
    assert main(["validate", "--data", str(FIXTURES)]) == 1
    assert "UNKNOWN_SPIRIT" in capsys.readouterr().out


def test_validate_missing_data_dir_exits_two(tmp_path, capsys):
    assert main(["validate", "--data", str(tmp_path / "nope")]) == 2
    assert "not found" in capsys.readouterr().err


def test_github_annotations_only_on_github(data_dir, capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    main(["validate", "--data", str(data_dir)])
    assert "::warning" not in capsys.readouterr().out

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    main(["validate", "--data", str(data_dir)])
    out = capsys.readouterr().out
    assert "::warning file=" in out
    assert "title=MISSING_DISTILLERY_ENTRY::" in out


def test_github_annotation_format_and_escaping():
    issue = Issue(Severity.ERROR, "SCHEMA", "50% bad\nline", "data/a,b.json")
    assert github_annotation(issue) == "::error file=data/a%2Cb.json,title=SCHEMA::50%25 bad%0Aline"
    no_file = Issue(Severity.WARNING, "X", "msg")
    assert github_annotation(no_file) == "::warning title=X::msg"


def test_format_issue():
    issue = Issue(Severity.WARNING, "X", "msg", "f.json")
    assert format_issue(issue) == "WARNING X [f.json]: msg"
