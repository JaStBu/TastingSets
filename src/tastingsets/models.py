"""Pydantic data models.

Every top-level model (``Document``) mirrors one MongoDB collection: ``model_dump()`` yields
a document with an ``_id`` key. ``SetMember`` is embedded in ``TastingSet``.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

import pycountry
from babel import Locale
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from tastingsets.languages import DEFAULT_LANGUAGE

SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MEMBER_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
#: ISO 3166-1 alpha-2 (``DE``) or ISO 3166-2 (``GB-SCT``).
COUNTRY_PATTERN = r"^[A-Z]{2}(-[A-Z0-9]{1,3})?$"

Slug = Annotated[str, Field(pattern=SLUG_PATTERN)]
CountryCode = Annotated[str, Field(pattern=COUNTRY_PATTERN)]
NonEmptyStr = Annotated[str, Field(min_length=1)]


def _require_default_language(value: dict[str, str]) -> dict[str, str]:
    if DEFAULT_LANGUAGE not in value:
        raise ValueError(f"must contain the language '{DEFAULT_LANGUAGE}'")
    return value


#: Text per language (``{"de": "...", "en": "..."}``); the default language is required.
LocalizedText = Annotated[dict[str, NonEmptyStr], AfterValidator(_require_default_language)]


class DuplicateMemberIdError(ValueError):
    """Raised when a tasting set contains the same ``member_id`` twice."""


class DuplicateGroupIdError(ValueError):
    """Raised when a tasting set contains the same ``group_id`` twice."""


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

    names: LocalizedText


class Distillery(NamedDocument):
    """A distillery.

    ``country`` is an ISO 3166-1 alpha-2 country code (``DE``) or an ISO 3166-2 region code
    (``GB-SCT``). ``region`` is an optional free-text proper noun for finer, non-ISO regions
    (e.g. ``Islay``, ``Speyside``); like ``name`` it is not translated.
    """

    country: CountryCode
    region: NonEmptyStr | None = None

    @field_validator("country")
    @classmethod
    def _check_country(cls, value: str) -> str:
        country, _, subdivision = value.partition("-")
        if country not in Locale("en").territories:
            raise ValueError(f"'{country}' is not a valid ISO 3166-1 alpha-2 country code")
        if subdivision and pycountry.subdivisions.get(code=value) is None:
            raise ValueError(f"'{value}' is not a valid ISO 3166-2 region code")
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
    notes: LocalizedText | None = None


class SetGroup(_Strict):
    """An arbitrary, display-only sub-group of a tasting set (e.g. "wine finish").

    Groups carry no meaning for statistics; they only show readers how the set is organised.
    """

    group_id: Slug
    names: LocalizedText
    description: LocalizedText | None = None
    members: Annotated[list[SetMember], Field(min_length=1)]


class TastingSet(Document):
    """A tasting set (e.g. an advent calendar).

    The name is localized (unlike distillery and spirit names, which are proper nouns).
    Either ``members`` (flat) or ``groups`` (each with its own ``members``) is given, never both.
    Order is preserved: groups in their defined order, members in file order.
    ``member_id`` is unique within the whole set, regardless of groups.
    """

    SEPARATOR: ClassVar[str] = "/"

    names: LocalizedText
    year: int | None = None
    members: list[SetMember] | None = None
    groups: Annotated[list[SetGroup], Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _check_structure(self) -> TastingSet:
        if (self.members is None) == (self.groups is None):
            raise ValueError("exactly one of 'members' or 'groups' must be given")
        seen_groups: set[str] = set()
        for group in self.groups or []:
            if group.group_id in seen_groups:
                raise DuplicateGroupIdError(f"duplicate group_id '{group.group_id}'")
            seen_groups.add(group.group_id)
        seen_members: set[str] = set()
        for member in self.all_members:
            if member.member_id in seen_members:
                raise DuplicateMemberIdError(f"duplicate member_id '{member.member_id}'")
            seen_members.add(member.member_id)
        return self

    @property
    def is_grouped(self) -> bool:
        return self.groups is not None

    @property
    def all_members(self) -> list[SetMember]:
        """Flat list of all members (group by group if grouped)."""
        if self.groups is not None:
            return [member for group in self.groups for member in group.members]
        return list(self.members or [])

    def group_of(self, member_id: str) -> SetGroup | None:
        """The group containing the member, or ``None`` (ungrouped set or unknown member)."""
        for group in self.groups or []:
            if any(member.member_id == member_id for member in group.members):
                return group
        return None

    def fqn(self, member: SetMember) -> str:
        """Fully qualified, globally unique name of a member: ``<set_id>/<member_id>``."""
        return f"{self.id}{self.SEPARATOR}{member.member_id}"
