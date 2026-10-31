"""Repository abstraction: where documents come from (JSON files now, MongoDB later)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tastingsets.models import Category, Distillery, Document, Spirit, TastingSet

#: Collection name (= folder name under ``data/``) -> model class.
COLLECTIONS: dict[str, type[Document]] = {
    "categories": Category,
    "distilleries": Distillery,
    "spirits": Spirit,
    "tasting_sets": TastingSet,
}


@dataclass(frozen=True)
class LoadError:
    """A problem found while loading documents.

    ``code`` is one of ``INVALID_JSON``, ``SCHEMA``, ``DUPLICATE_ID``, ``DUPLICATE_MEMBER_ID``.
    """

    code: str
    collection: str
    message: str
    file: str | None = None
    object_id: str | None = None


class Repository(Protocol):
    """Read access to all collections."""

    @property
    def load_errors(self) -> list[LoadError]:
        """Problems found while loading; documents with errors are not returned."""
        ...

    def categories(self) -> list[Category]: ...

    def distilleries(self) -> list[Distillery]: ...

    def spirits(self) -> list[Spirit]: ...

    def tasting_sets(self) -> list[TastingSet]: ...

    def source_of(self, collection: str, doc_id: str) -> str | None:
        """Where a document came from (e.g. a file path), for error messages."""
        ...
