"""Template-based task decomposition (MVP)."""

from __future__ import annotations

import re
from typing import Any

from roboweave_interfaces.task import PlanGraph, PlanNode

from .skill_selector import SkillSelector


class TaskDecomposer:
    """Template-based task decomposition.

    Matches instructions against configured templates using
    case-insensitive substring matching, then instantiates
    PlanNode objects from the template skeleton.
    """

    def __init__(
        self, templates: list[dict[str, Any]], skill_selector: SkillSelector
    ) -> None:
        """Load templates. Each template has 'pattern', 'regex', and 'nodes' keys."""
        self._templates = templates
        self._skill_selector = skill_selector

    def decompose(
        self,
        instruction: str,
        task_id: str,
        scene_context: dict[str, Any] | None = None,
    ) -> PlanGraph | None:
        """Match instruction against templates, produce PlanGraph or None."""
        instruction_lower = instruction.lower()

        for template in self._templates:
            pattern = template["pattern"].lower()
            if pattern not in instruction_lower:
                continue

            # Extract named groups via regex if provided
            captures: dict[str, str] = {}
            regex = template.get("regex")
            if regex:
                match = re.search(regex, instruction, re.IGNORECASE)
                if match:
                    captures = match.groupdict()

            # Build a mapping from skill_name -> node_id for depends_on resolution
            template_nodes = template["nodes"]
            skill_to_node_id: dict[str, str] = {}
            nodes: list[PlanNode] = []

            for i, node_def in enumerate(template_nodes):
                node_id = f"{task_id}_node_{i}"
                skill_name = node_def["skill_name"]
                skill_to_node_id[skill_name] = node_id

                # Validate skill exists via SkillSelector
                self._skill_selector.select(skill_name)

                # Resolve input placeholders with captured groups
                inputs = dict(node_def.get("inputs", {}))
                for key, value in inputs.items():
                    if isinstance(value, str):
                        for cap_name, cap_value in captures.items():
                            inputs[key] = inputs[key].replace(
                                f"{{{cap_name}}}", cap_value
                            )

                # Resolve depends_on from skill names to node_ids
                depends_on_skills = node_def.get("depends_on", [])
                depends_on_ids = [
                    skill_to_node_id[dep]
                    for dep in depends_on_skills
                    if dep in skill_to_node_id
                ]

                node = PlanNode(
                    node_id=node_id,
                    node_type=node_def.get("node_type", "skill"),
                    skill_name=skill_name,
                    inputs=inputs,
                    depends_on=depends_on_ids,
                )
                nodes.append(node)

            return PlanGraph(
                plan_id=f"{task_id}_plan",
                task_id=task_id,
                nodes=nodes,
            )

        return None
