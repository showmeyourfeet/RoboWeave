"""SkillRegistry: In-process registry mapping skill names to VLASkillBase instances.

Pure Python — no ROS2 imports.
"""

from __future__ import annotations

from roboweave_interfaces.skill import SkillDescriptor

from .vla_skill_base import VLASkillBase


class SkillRegistry:
    """In-process registry mapping skill names to VLASkillBase instances."""

    def __init__(self) -> None:
        self._skills: dict[str, VLASkillBase] = {}

    def register(self, skill: VLASkillBase) -> None:
        """Register a skill. Raises ValueError on duplicate or invalid metadata."""
        name = skill.skill_name
        if not name:
            raise ValueError("skill_name must be non-empty")
        if not skill.supported_instructions:
            raise ValueError(
                f"Skill '{name}' must have at least one supported_instructions entry"
            )
        if not skill.action_space.supported_action_types:
            raise ValueError(
                f"Skill '{name}' action_space must have at least one supported_action_types entry"
            )
        if name in self._skills:
            raise ValueError(f"Skill '{name}' is already registered")
        self._skills[name] = skill

    def get(self, skill_name: str) -> VLASkillBase | None:
        """Look up a skill by name. Returns None if not found."""
        return self._skills.get(skill_name)

    def list_skills(self) -> list[SkillDescriptor]:
        """Return descriptors for all registered skills."""
        return [skill.descriptor for skill in self._skills.values()]

    def __len__(self) -> int:
        return len(self._skills)
