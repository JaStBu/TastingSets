"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from tastingsets.repository.json_repository import JsonRepository
from tastingsets.schemas import write_schemas
from tastingsets.site.builder import BuildError, build
from tastingsets.validation import Issue, Severity, has_errors, validate

DEFAULT_DATA_DIR = "data"
DEFAULT_LANGUAGES = ["de"]


def format_issue(issue: Issue) -> str:
    """Human readable single-line representation."""
    where = f" [{issue.file}]" if issue.file else ""
    return f"{issue.severity.name:<7} {issue.code}{where}: {issue.message}"


def github_annotation(issue: Issue) -> str:
    """GitHub Actions workflow command (``::warning file=...::message``)."""

    def escape_data(text: str) -> str:
        return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

    def escape_property(text: str) -> str:
        return escape_data(text).replace(":", "%3A").replace(",", "%2C")

    level = "error" if issue.severity is Severity.ERROR else "warning"
    properties = []
    if issue.file:
        properties.append(f"file={escape_property(issue.file)}")
    properties.append(f"title={escape_property(issue.code)}")
    return f"::{level} {','.join(properties)}::{escape_data(issue.message)}"


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        repo = JsonRepository(args.data)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    issues = validate(repo)
    on_github = os.environ.get("GITHUB_ACTIONS") == "true"
    for issue in issues:
        print(format_issue(issue))
        if on_github:
            print(github_annotation(issue))
    errors = sum(1 for i in issues if i.severity is Severity.ERROR)
    warnings = len(issues) - errors
    print(f"{errors} error(s), {warnings} warning(s)")
    if has_errors(issues) or (args.strict and issues):
        return 1
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    try:
        repo = JsonRepository(args.data)
        written = build(repo, args.out, base_url=args.base_url, languages=args.languages)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BuildError as exc:
        for issue in exc.issues:
            print(format_issue(issue), file=sys.stderr)
        print(f"error: {exc}; site not generated", file=sys.stderr)
        return 1
    print(f"wrote {len(written)} file(s) to {args.out}")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    written = write_schemas(args.out)
    print(f"wrote {len(written)} schema(s) to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tastingsets")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="validate the data directory")
    validate_parser.add_argument("--data", type=Path, default=Path(DEFAULT_DATA_DIR))
    validate_parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors (exit code 1)"
    )
    validate_parser.set_defaults(func=cmd_validate)

    build_parser_ = subparsers.add_parser("build", help="generate the static site")
    build_parser_.add_argument("--data", type=Path, default=Path(DEFAULT_DATA_DIR))
    build_parser_.add_argument("--out", type=Path, default=Path("dist"))
    build_parser_.add_argument("--base-url", default="/", help="e.g. /TastingSets/")
    build_parser_.add_argument("--languages", nargs="+", default=DEFAULT_LANGUAGES)
    build_parser_.set_defaults(func=cmd_build)

    schema_parser = subparsers.add_parser("schema", help="write JSON schemas of the data files")
    schema_parser.add_argument("--out", type=Path, default=Path("schemas"))
    schema_parser.set_defaults(func=cmd_schema)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)
