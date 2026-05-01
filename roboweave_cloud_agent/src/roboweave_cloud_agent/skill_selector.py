"""Keyword-based skill selection (MVP)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roboweave_interfaces.skill import SkillDescriptor


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase words, splitting on whitespace and underscores."""
    return set(re.split(r"[\s_]+", text.lower())) - {""}


class SkillSelector:
    """Keyword-based skill selection.

    Tokenizes query strings and skill names/descriptions, then picks
    the skill with the highest token overlap.
    """

    def __init__(self, descriptors: list[SkillDescriptor]) -> None:
        """Register skill descriptors."""
        self._descriptors = list(descriptors)
        # Pre-tokenize skill name + description for each descriptor
        self._tokens: list[set[str]] = [
            _tokenize(f"{d.name} {d.description}") for d in self._descriptors
        ]

    def select(self, query: str) -> SkillDescriptor | None:
        """Return the best-matching skill, or None if no overlap."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return None

        best_score = 0
        best_descriptor = None

        for descriptor, skill_tokens in zip(self._descriptors, self._tokens):
            overlap = len(query_tokens & skill_tokens)
            if overlap > best_score:
                best_score = overlap
                best_descriptor = descriptor

        return best_descriptor if best_score > 0 else None

    def list_skills(self) -> list[str]:
        """Return all registered skill names."""
        return [d.name for d in self._descriptors]
