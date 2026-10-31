"""Pydantic data models.

Every top-level model (``Document``) mirrors one MongoDB collection: ``model_dump()`` yields
a document with an ``_id`` key. ``SetMember`` is embedded in ``TastingSet``.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from babel import Locale
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MEMBER_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
REQUIRED_LANGUAGE = "de"

Slug = Annotated[str, Field(pattern=SLUG_PATTERN)]
NonEmptyStr = Annotated[str, Field(min_length=1)]


class DuplicateMemberIdError(ValueError):
    """Raised when a tasting set contains the same ``member_id`` twice."""


class _Strict(BaseModel):
    """Common configuration: unknown fields are errors, aliases are used for (de)serialization."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )


class Document(_Strict):
    """Base class for top-level documents (one MongoDB collection each)."""

    id: Slug = Field(alias="_id")


class NamedDocument(Document):
    """Document with a ``name`` and an optional ``display_name``."""

    name: NonEmptyStr
    display_name: NonEmptyStr | None = None

    @property
    def label(self) -> str:
        """Text to show to users: ``display_name`` if set, otherwise ``name``."""
        return self.display_name or self.name


class Category(Document):
    """Kind of spirit (e.g. single malt whisky, grappa) with localized names."""

    names: dict[str, NonEmptyStr]

    @field_validator("names")
    @classmethod
    def _require_default_language(cls, value: dict[str, str]) -> dict[str, str]:
        if REQUIRED_LANGUAGE not in value:
            raise ValueError(f"names must contain the language '{REQUIRED_LANGUAGE}'")
        return value


class Distillery(NamedDocument):
    """A distillery; ``country`` is an ISO 3166-1 alpha-2 code."""

    country: str

    @field_validator("country")
    @classmethod
    def _check_country(cls, value: str) -> str:
        if len(value) != 2 or not value.isupper() or value not in Locale("en").territories:
            raise ValueError(f"'{value}' is not a valid upper-case ISO 3166-1 alpha-2 country code")
        return value


class Spirit(NamedDocument):
    """A bottled spirit.

    The distillery is referenced via ``distillery_id``. If no distillery entry exists, only
    ``distillery_name`` may be given as free-text fallback; at least one of both is required.
    """

    category_id: Slug
    abv: Annotated[float, Field(gt=0, le=100)]
    distillery_id: Slug | None = None
    distillery_name: NonEmptyStr | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def _require_distillery_reference(self) -> Spirit:
        if self.distillery_id is None and self.distillery_name is None:
            raise ValueError("either distillery_id or distillery_name must be set")
        return self


class SetMember(_Strict):
    """One numbered bottle of a tasting set. Unique only within its tasting set."""

    member_id: Annotated[str, Field(pattern=MEMBER_ID_PATTERN)]
    spirit_id: Slug
    notes: NonEmptyStr | None = None


class TastingSet(NamedDocument):
    """A tasting set (e.g. an advent calendar) with its members in file order."""

    SEPARATOR: ClassVar[str] = "/"

    year: int | None = None
    members: list[SetMember]

    @field_validator("members")
    @classmethod
    def _unique_member_ids(cls, value: list[SetMember]) -> list[SetMember]:
        seen: set[str] = set()
        for member in value:
            if member.member_id in seen:
                raise DuplicateMemberIdError(f"duplicate member_id '{member.member_id}'")
            seen.add(member.member_id)
        return value

    def fqn(self, member: SetMember) -> str:
        """Fully qualified, globally unique name of a member: ``<set_id>/<member_id>``."""
        return f"{self.id}{self.SEPARATOR}{member.member_id}"
