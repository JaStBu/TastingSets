"""Catalog: indexed documents with resolved references (independent of the storage backend)."""

from __future__ import annotations

from dataclasses import dataclass

from tastingsets.models import Category, Distillery, SetMember, Spirit, TastingSet
from tastingsets.repository.base import Repository


class UnknownReferenceError(LookupError):
    """A referenced document does not exist."""


@dataclass(frozen=True)
class ResolvedMember:
    """A set member with all referenced documents resolved."""

    set_id: str
    fqn: str
    member_id: str
    notes: str | None
    spirit: Spirit
    category: Category
    distillery: Distillery | None

    @property
    def distillery_label(self) -> str | None:
        """Distillery display name; falls back to the free-text ``distillery_name``."""
        if self.distillery is not None:
            return self.distillery.label
        return self.spirit.distillery_name

    @property
    def country(self) -> str | None:
        """ISO country code, known only if a distillery entry exists."""
        return self.distillery.country if self.distillery is not None else None


@dataclass(frozen=True)
class Catalog:
    """All documents indexed by ``_id`` (insertion order is preserved)."""

    categories: dict[str, Category]
    distilleries: dict[str, Distillery]
    spirits: dict[str, Spirit]
    tasting_sets: dict[str, TastingSet]

    @classmethod
    def from_repository(cls, repo: Repository) -> Catalog:
        return cls(
            categories={d.id: d for d in repo.categories()},
            distilleries={d.id: d for d in repo.distilleries()},
            spirits={d.id: d for d in repo.spirits()},
            tasting_sets={d.id: d for d in repo.tasting_sets()},
        )

    def resolve(self, tasting_set: TastingSet, member: SetMember) -> ResolvedMember:
        """Resolve all references of one member; raises ``UnknownReferenceError``."""
        spirit = self.spirits.get(member.spirit_id)
        if spirit is None:
            raise UnknownReferenceError(f"unknown spirit '{member.spirit_id}'")
        category = self.categories.get(spirit.category_id)
        if category is None:
            raise UnknownReferenceError(f"unknown category '{spirit.category_id}'")
        distillery = None
        if spirit.distillery_id is not None:
            distillery = self.distilleries.get(spirit.distillery_id)
            if distillery is None:
                raise UnknownReferenceError(f"unknown distillery '{spirit.distillery_id}'")
        return ResolvedMember(
            set_id=tasting_set.id,
            fqn=tasting_set.fqn(member),
            member_id=member.member_id,
            notes=member.notes,
            spirit=spirit,
            category=category,
            distillery=distillery,
        )

    def resolve_set(self, set_id: str) -> list[ResolvedMember]:
        """All members of a set in file order."""
        tasting_set = self._get_set(set_id)
        return [self.resolve(tasting_set, member) for member in tasting_set.members]

    def resolve_member(self, fqn: str) -> ResolvedMember:
        """Resolve ``<set_id>/<member_id>``."""
        set_id, separator, member_id = fqn.partition(TastingSet.SEPARATOR)
        tasting_set = self._get_set(set_id)
        for member in tasting_set.members:
            if separator and member.member_id == member_id:
                return self.resolve(tasting_set, member)
        raise UnknownReferenceError(f"unknown set member '{fqn}'")

    def _get_set(self, set_id: str) -> TastingSet:
        try:
            return self.tasting_sets[set_id]
        except KeyError:
            raise UnknownReferenceError(f"unknown tasting set '{set_id}'") from None
