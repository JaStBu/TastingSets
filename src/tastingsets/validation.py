"""Validation of the whole data set: schema problems and broken references."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tastingsets.models import Spirit
from tastingsets.repository.base import Repository


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    """One validation finding.

    Error codes: ``INVALID_JSON``, ``SCHEMA``, ``DUPLICATE_ID``, ``DUPLICATE_MEMBER_ID``,
    ``UNKNOWN_SPIRIT``, ``UNKNOWN_CATEGORY``, ``UNKNOWN_DISTILLERY``.
    Warning codes: ``MISSING_DISTILLERY_ENTRY``, ``DISTILLERY_NAME_MATCHES_ENTRY``,
    ``UNUSED_SPIRIT``.
    """

    severity: Severity
    code: str
    message: str
    file: str | None = None
    object_id: str | None = None


def _spirit_issue(
    repo: Repository, spirit: Spirit, severity: Severity, code: str, message: str
) -> Issue:
    return Issue(
        severity,
        code,
        f"spirit '{spirit.id}': {message}",
        repo.source_of("spirits", spirit.id),
        spirit.id,
    )


def _check_spirits(repo: Repository) -> list[Issue]:
    issues: list[Issue] = []
    category_ids = {c.id for c in repo.categories()}
    distilleries = repo.distilleries()
    distillery_ids = {d.id for d in distilleries}
    distillery_names = {n.casefold() for d in distilleries for n in (d.name, d.label)}

    for spirit in repo.spirits():
        if spirit.category_id not in category_ids:
            issues.append(
                _spirit_issue(
                    repo,
                    spirit,
                    Severity.ERROR,
                    "UNKNOWN_CATEGORY",
                    f"category_id '{spirit.category_id}' does not exist",
                )
            )
        if spirit.distillery_id is not None:
            if spirit.distillery_id not in distillery_ids:
                issues.append(
                    _spirit_issue(
                        repo,
                        spirit,
                        Severity.ERROR,
                        "UNKNOWN_DISTILLERY",
                        f"distillery_id '{spirit.distillery_id}' does not exist "
                        "(use distillery_name if the distillery has no entry)",
                    )
                )
        elif spirit.distillery_name is not None:
            if spirit.distillery_name.casefold() in distillery_names:
                issues.append(
                    _spirit_issue(
                        repo,
                        spirit,
                        Severity.WARNING,
                        "DISTILLERY_NAME_MATCHES_ENTRY",
                        f"distillery_name '{spirit.distillery_name}' matches an existing "
                        "distillery; use distillery_id instead",
                    )
                )
            else:
                issues.append(
                    _spirit_issue(
                        repo,
                        spirit,
                        Severity.WARNING,
                        "MISSING_DISTILLERY_ENTRY",
                        f"distillery '{spirit.distillery_name}' has no entry in the "
                        "distillery list",
                    )
                )
    return issues


def _check_tasting_sets(repo: Repository) -> list[Issue]:
    issues: list[Issue] = []
    spirit_ids = {s.id for s in repo.spirits()}
    used: set[str] = set()

    for tasting_set in repo.tasting_sets():
        for member in tasting_set.members:
            used.add(member.spirit_id)
            if member.spirit_id not in spirit_ids:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "UNKNOWN_SPIRIT",
                        f"tasting set '{tasting_set.id}', member '{member.member_id}': "
                        f"spirit_id '{member.spirit_id}' does not exist",
                        repo.source_of("tasting_sets", tasting_set.id),
                        tasting_set.id,
                    )
                )

    for spirit in repo.spirits():
        if spirit.id not in used:
            issues.append(
                _spirit_issue(
                    repo,
                    spirit,
                    Severity.WARNING,
                    "UNUSED_SPIRIT",
                    "is not used in any tasting set",
                )
            )
    return issues


def validate(repo: Repository) -> list[Issue]:
    """Return all issues of the data held by ``repo`` (empty list = everything is fine)."""
    issues = [
        Issue(Severity.ERROR, e.code, e.message, e.file, e.object_id) for e in repo.load_errors
    ]
    issues += _check_spirits(repo)
    issues += _check_tasting_sets(repo)
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity is Severity.ERROR for i in issues)
