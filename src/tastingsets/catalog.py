"""Catalog: indexed documents with resolved references (independent of the storage backend)."""

from __future__ import annotations

from dataclasses import dataclass

from tastingsets.models import Category, Distillery, SetGroup, SetMember, Spirit, TastingSet
from tastingsets.repository.base import Repository


class UnknownReferenceError(LookupError):
    """A referenced document does not exist."""


@dataclass(frozen=True)
class ResolvedMember:
    """A set member with all referenced documents resolved."""

    set_id: str
    fqn: str
    member_id: str
    notes: dict[str, str] | None
    spirit: Spirit
    category: Category
    distillery: Distillery | None
    group_id: str | None = None

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
class ResolvedGroup:
    """Members shown together. ``group`` is ``None`` for sets without groups."""

    group: SetGroup | None
    members: list[ResolvedMember]


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
            group_id=group.group_id if (group := tasting_set.group_of(member.member_id)) else None,
        )

    def resolve_set(self, set_id: str) -> list[ResolvedMember]:
        """All members of a set as flat list (groups in defined order, members in file order)."""
        tasting_set = self._get_set(set_id)
        return [self.resolve(tasting_set, member) for member in tasting_set.all_members]

    def resolve_groups(self, set_id: str) -> list[ResolvedGroup]:
        """Members organised for display; one group with ``group=None`` if the set is flat."""
        tasting_set = self._get_set(set_id)
        if tasting_set.groups is None:
            return [ResolvedGroup(None, self.resolve_set(set_id))]
        return [
            ResolvedGroup(group, [self.resolve(tasting_set, m) for m in group.members])
            for group in tasting_set.groups
        ]

    def resolve_member(self, fqn: str) -> ResolvedMember:
        """Resolve ``<set_id>/<member_id>``."""
        set_id, separator, member_id = fqn.partition(TastingSet.SEPARATOR)
        tasting_set = self._get_set(set_id)
        for member in tasting_set.all_members:
            if separator and member.member_id == member_id:
                return self.resolve(tasting_set, member)
        raise UnknownReferenceError(f"unknown set member '{fqn}'")

    def _get_set(self, set_id: str) -> TastingSet:
        try:
            return self.tasting_sets[set_id]
        except KeyError:
            raise UnknownReferenceError(f"unknown tasting set '{set_id}'") from None
