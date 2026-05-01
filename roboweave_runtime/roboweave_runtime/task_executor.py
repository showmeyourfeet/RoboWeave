"""TaskExecutor — PlanGraph validation, BT construction, and tick-based execution."""

from __future__ import annotations

import json
from collections import deque
from typing import Any, Callable

from roboweave_interfaces.task import PlanGraph, PlanNode
from roboweave_interfaces.skill import SkillCall
from roboweave_interfaces.event import EventType
from roboweave_interfaces.errors import Severity

from .bt_nodes.skill_action import BTStatus, SkillActionNode
from .bt_nodes.condition_check import ConditionCheckNode
from .execution_monitor import ExecutionMonitor
from .skill_orchestrator import SkillOrchestrator
from .world_model import WorldModel


class _SequenceNode:
    """Internal sequence node: ticks children in order, fails on first failure."""

    def __init__(self, name: str, children: list[Any]) -> None:
        self.name = name
        self.children = children
        self._current_index = 0
        self.status: BTStatus = BTStatus.RUNNING

    def tick(self) -> BTStatus:
        while self._current_index < len(self.children):
            child = self.children[self._current_index]
            result = child.tick()
            if result == BTStatus.RUNNING:
                self.status = BTStatus.RUNNING
                return BTStatus.RUNNING
            elif result == BTStatus.FAILURE:
                self.status = BTStatus.FAILURE
                return BTStatus.FAILURE
            # SUCCESS — move to next child
            self._current_index += 1
        self.status = BTStatus.SUCCESS
        return BTStatus.SUCCESS

    def reset(self) -> None:
        self._current_index = 0
        for child in self.children:
            child.reset()
        self.status = BTStatus.RUNNING


class TaskExecutor:
    """Pure Python PlanGraph → BT conversion and tick-based execution."""

    def __init__(
        self,
        skill_orchestrator: SkillOrchestrator,
        world_model: WorldModel,
        execution_monitor: ExecutionMonitor,
        tick_hz: float = 10.0,
    ) -> None:
        self._skill_orchestrator = skill_orchestrator
        self._world_model = world_model
        self._execution_monitor = execution_monitor
        self.tick_hz = tick_hz

        self._active_tree: _SequenceNode | None = None
        self._active_task_id: str | None = None
        self._active_plan: PlanGraph | None = None
        self._paused: bool = False
        self._task_status: str = "pending"

        # Callbacks
        self.on_task_status: (
            Callable[[str, str, float, str, str, str], None] | None
        ) = None

    # --- Plan dispatch ---

    def dispatch_plan(self, plan_json: str) -> tuple[bool, str]:
        """Deserialize, validate, and begin executing a PlanGraph."""
        try:
            data = json.loads(plan_json)
        except (json.JSONDecodeError, TypeError) as e:
            return False, f"Invalid JSON: {e}"

        try:
            plan = PlanGraph(**data)
        except Exception as e:
            return False, f"Invalid PlanGraph: {e}"

        ok, msg = self.validate_plan_graph(plan)
        if not ok:
            return False, msg

        tree = self.build_behaviour_tree(plan)
        self._active_tree = tree
        self._active_task_id = plan.task_id
        self._active_plan = plan
        self._paused = False
        self._task_status = "running"

        # Publish task_started event
        event = self._execution_monitor.create_event(
            task_id=plan.task_id,
            node_id="",
            event_type=EventType.TASK_STARTED,
            severity=Severity.INFO,
            message=f"Task {plan.task_id} started",
        )
        self._execution_monitor.publish_event(event)
        self._notify_task_status()

        return True, f"Plan {plan.plan_id} dispatched"

    def validate_plan_graph(self, plan: PlanGraph) -> tuple[bool, str]:
        """Validate DAG (no cycles via Kahn's algorithm) and skill references."""
        nodes = plan.nodes
        if not nodes:
            return True, "Empty plan is valid"

        # Build adjacency and in-degree
        node_ids = {n.node_id for n in nodes}
        in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
        adjacency: dict[str, list[str]] = {n.node_id: [] for n in nodes}

        for node in nodes:
            for dep in node.depends_on:
                if dep not in node_ids:
                    return False, f"Unknown dependency: {dep}"
                adjacency[dep].append(node.node_id)
                in_degree[node.node_id] += 1

        # Kahn's algorithm
        queue: deque[str] = deque()
        for nid, deg in in_degree.items():
            if deg == 0:
                queue.append(nid)

        sorted_count = 0
        while queue:
            current = queue.popleft()
            sorted_count += 1
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if sorted_count != len(nodes):
            return False, "PlanGraph contains a cycle"

        # Validate skill references
        for node in nodes:
            if node.skill_name:
                if not self._skill_orchestrator.is_skill_registered(node.skill_name):
                    return (
                        False,
                        f"Skill not registered: {node.skill_name}",
                    )

        return True, "Valid"

    def build_behaviour_tree(self, plan: PlanGraph) -> _SequenceNode:
        """Convert PlanGraph to a lightweight internal BT respecting depends_on ordering."""
        # Topological sort to determine execution order
        nodes = plan.nodes
        node_map = {n.node_id: n for n in nodes}
        in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
        adjacency: dict[str, list[str]] = {n.node_id: [] for n in nodes}

        for node in nodes:
            for dep in node.depends_on:
                adjacency[dep].append(node.node_id)
                in_degree[node.node_id] += 1

        queue: deque[str] = deque()
        for nid, deg in in_degree.items():
            if deg == 0:
                queue.append(nid)

        ordered: list[str] = []
        while queue:
            current = queue.popleft()
            ordered.append(current)
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Build BT nodes in topological order
        bt_children: list[Any] = []
        for node_id in ordered:
            plan_node = node_map[node_id]
            if plan_node.skill_name:
                skill_call = SkillCall(
                    skill_call_id=f"{plan.task_id}_{node_id}",
                    skill_name=plan_node.skill_name,
                    task_id=plan.task_id,
                    inputs=plan_node.inputs,
                    constraints=plan_node.constraints,
                    timeout_ms=plan_node.timeout_ms or 5000,
                )
                bt_node = SkillActionNode(
                    name=node_id,
                    skill_call=skill_call,
                    orchestrator=self._skill_orchestrator,
                )
            else:
                # Condition or other node type — use a condition check
                bt_node = ConditionCheckNode(
                    name=node_id,
                    condition_fn=lambda ws: True,  # Default pass-through
                    world_model=self._world_model,
                )
            bt_children.append(bt_node)

        return _SequenceNode(name=f"plan_{plan.plan_id}", children=bt_children)

    # --- Task control ---

    def pause(self, task_id: str) -> tuple[bool, str]:
        if self._active_task_id != task_id:
            return False, f"No active task with id: {task_id}"
        self._paused = True
        self._task_status = "paused"
        self._notify_task_status()
        return True, "Paused"

    def resume(self, task_id: str) -> tuple[bool, str]:
        if self._active_task_id != task_id:
            return False, f"No active task with id: {task_id}"
        self._paused = False
        self._task_status = "running"
        self._notify_task_status()
        return True, "Resumed"

    def cancel(self, task_id: str) -> tuple[bool, str]:
        if self._active_task_id != task_id:
            return False, f"No active task with id: {task_id}"
        self._task_status = "cancelled"
        self._active_tree = None
        self._active_task_id = None
        self._active_plan = None
        self._paused = False
        self._notify_task_status()
        return True, "Cancelled"

    # --- Tick ---

    def tick(self) -> None:
        """Single BT tick. Updates task status and publishes TaskStatus."""
        if self._active_tree is None or self._paused:
            return

        try:
            result = self._active_tree.tick()
        except Exception:
            self._task_status = "failed"
            self._notify_task_status()
            self._active_tree = None
            return

        if result == BTStatus.SUCCESS:
            self._task_status = "succeeded"
            event = self._execution_monitor.create_event(
                task_id=self._active_task_id or "",
                node_id="",
                event_type=EventType.TASK_COMPLETED,
                severity=Severity.INFO,
                message="Task completed successfully",
            )
            self._execution_monitor.publish_event(event)
            self._notify_task_status()
            self._active_tree = None
        elif result == BTStatus.FAILURE:
            self._task_status = "failed"
            event = self._execution_monitor.create_event(
                task_id=self._active_task_id or "",
                node_id="",
                event_type=EventType.TASK_FAILED,
                severity=Severity.ERROR,
                message="Task failed",
            )
            self._execution_monitor.publish_event(event)
            self._notify_task_status()
            self._active_tree = None

    # --- Internal ---

    def _notify_task_status(self) -> None:
        if self.on_task_status and self._active_task_id:
            self.on_task_status(
                self._active_task_id,
                self._task_status,
                0.0,  # progress
                "",   # current_node_id
                "",   # failure_code
                "",   # message
            )
