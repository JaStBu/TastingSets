"""Repository reading ``<data_dir>/<collection>/*.json`` files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tastingsets.models import (
    Category,
    Distillery,
    Document,
    DuplicateGroupIdError,
    DuplicateMemberIdError,
    Spirit,
    TastingSet,
)
from tastingsets.repository.base import COLLECTIONS, LoadError


def _display_path(path: Path) -> str:
    """Path relative to the current directory if possible (matches GitHub annotations)."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _format_pydantic_errors(exc: ValidationError) -> list[tuple[str, str]]:
    """Return ``(code, message)`` per Pydantic error."""
    result = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"])
        message = f"{location}: {err['msg']}" if location else err["msg"]
        cause = err.get("ctx", {}).get("error")
        if isinstance(cause, DuplicateMemberIdError):
            code = "DUPLICATE_MEMBER_ID"
        elif isinstance(cause, DuplicateGroupIdError):
            code = "DUPLICATE_GROUP_ID"
        else:
            code = "SCHEMA"
        result.append((code, message))
    return result


class JsonRepository:
    """Loads all JSON files of every collection folder (sorted by file name).

    A file contains either a single object or a list of objects. Problems do not abort loading;
    they are collected in :attr:`load_errors` and the offending documents are skipped.
    """

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_dir():
            raise FileNotFoundError(f"data directory not found: {self.data_dir}")
        self._errors: list[LoadError] = []
        self._documents: dict[str, list[Any]] = {}
        self._sources: dict[tuple[str, str], str] = {}
        for collection, model in COLLECTIONS.items():
            self._documents[collection] = self._load_collection(collection, model)

    # -- Repository protocol -------------------------------------------------------------------

    @property
    def load_errors(self) -> list[LoadError]:
        return list(self._errors)

    def categories(self) -> list[Category]:
        return list(self._documents["categories"])

    def distilleries(self) -> list[Distillery]:
        return list(self._documents["distilleries"])

    def spirits(self) -> list[Spirit]:
        return list(self._documents["spirits"])

    def tasting_sets(self) -> list[TastingSet]:
        return list(self._documents["tasting_sets"])

    def source_of(self, collection: str, doc_id: str) -> str | None:
        return self._sources.get((collection, doc_id))

    # -- loading -------------------------------------------------------------------------------

    def _load_collection(self, collection: str, model: type[Document]) -> list[Any]:
        folder = self.data_dir / collection
        documents: list[Any] = []
        if not folder.is_dir():
            return documents
        for path in sorted(folder.glob("*.json")):
            shown = _display_path(path)
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                self._errors.append(LoadError("INVALID_JSON", collection, str(exc), shown))
                continue
            entries = raw if isinstance(raw, list) else [raw]
            for index, entry in enumerate(entries):
                self._load_entry(collection, model, entry, index, shown, documents)
        return documents

    def _load_entry(
        self,
        collection: str,
        model: type[Document],
        entry: Any,
        index: int,
        shown: str,
        documents: list[Any],
    ) -> None:
        raw_id = entry.get("_id") if isinstance(entry, dict) else None
        object_id = raw_id if isinstance(raw_id, str) else None
        try:
            document = model.model_validate(entry)
        except ValidationError as exc:
            for code, message in _format_pydantic_errors(exc):
                self._errors.append(
                    LoadError(code, collection, f"entry {index}: {message}", shown, object_id)
                )
            return
        key = (collection, document.id)
        if key in self._sources:
            self._errors.append(
                LoadError(
                    "DUPLICATE_ID",
                    collection,
                    f"entry {index}: duplicate _id '{document.id}' "
                    f"(first defined in {self._sources[key]})",
                    shown,
                    document.id,
                )
            )
            return
        self._sources[key] = shown
        documents.append(document)
