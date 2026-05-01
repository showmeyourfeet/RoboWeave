"""Shared fixtures for roboweave_cloud_agent tests."""

from __future__ import annotations

import types
from typing import Any

import pytest

from roboweave_interfaces.skill import SkillCategory, SkillDescriptor


@pytest.fixture
def sample_skill_descriptors() -> list[SkillDescriptor]:
    """Sample skill descriptors for testing."""
    return [
        SkillDescriptor(
            name="detect_object",
            category=SkillCategory.PERCEPTION,
            description="Detect and localize a target object in the scene",
            version="0.1.0",
        ),
        SkillDescriptor(
            name="plan_grasp",
            category=SkillCategory.PLANNING,
            description="Plan a grasp pose for a detected object",
            version="0.1.0",
        ),
        SkillDescriptor(
            name="plan_motion",
            category=SkillCategory.PLANNING,
            description="Plan a collision-free motion trajectory",
            version="0.1.0",
        ),
        SkillDescriptor(
            name="execute_grasp",
            category=SkillCategory.CONTROL,
            description="Execute a grasp by closing the gripper",
            version="0.1.0",
        ),
        SkillDescriptor(
            name="open_gripper",
            category=SkillCategory.CONTROL,
            description="Open the gripper to release an object",
            version="0.1.0",
        ),
        SkillDescriptor(
            name="retract",
            category=SkillCategory.CONTROL,
            description="Retract the arm to a safe position after placing",
            version="0.1.0",
        ),
    ]


@pytest.fixture
def sample_templates() -> list[dict[str, Any]]:
    """Sample task templates for testing."""
    return [
        {
            "pattern": "pick up",
            "regex": "pick up (?P<object>.+)",
            "nodes": [
                {"skill_name": "detect_object", "node_type": "skill", "depends_on": [], "inputs": {"target": "{object}"}},
                {"skill_name": "plan_grasp", "node_type": "skill", "depends_on": ["detect_object"], "inputs": {}},
                {"skill_name": "plan_motion", "node_type": "skill", "depends_on": ["plan_grasp"], "inputs": {}},
                {"skill_name": "execute_grasp", "node_type": "skill", "depends_on": ["plan_motion"], "inputs": {}},
            ],
        },
        {
            "pattern": "place",
            "regex": "place (?P<object>.+) on (?P<surface>.+)",
            "nodes": [
                {"skill_name": "plan_motion", "node_type": "skill", "depends_on": [], "inputs": {"target": "{surface}"}},
                {"skill_name": "open_gripper", "node_type": "skill", "depends_on": ["plan_motion"], "inputs": {}},
                {"skill_name": "retract", "node_type": "skill", "depends_on": ["open_gripper"], "inputs": {}},
            ],
        },
    ]


@pytest.fixture
def sample_config(sample_templates, sample_skill_descriptors) -> dict[str, Any]:
    """Sample agent config dict for testing."""
    return {
        "server": {"host": "0.0.0.0", "port": 50051, "shutdown_timeout_sec": 5},
        "task_templates": sample_templates,
        "skill_descriptors": [d.model_dump() for d in sample_skill_descriptors],
    }


def make_plan_node_proto(**kwargs) -> types.SimpleNamespace:
    """Create a SimpleNamespace mimicking PlanNodeProto."""
    return types.SimpleNamespace(
        schema_version=kwargs.get("schema_version", "roboweave.v1"),
        node_id=kwargs.get("node_id", ""),
        node_type=kwargs.get("node_type", "skill"),
        skill_name=kwargs.get("skill_name", ""),
        inputs_envelope_json=kwargs.get("inputs_envelope_json", ""),
        constraints_envelope_json=kwargs.get("constraints_envelope_json", ""),
        depends_on=kwargs.get("depends_on", []),
        preconditions=kwargs.get("preconditions", []),
        postconditions=kwargs.get("postconditions", []),
        retry_policy=kwargs.get("retry_policy", None),
        timeout_ms=kwargs.get("timeout_ms", 0),
        on_success=kwargs.get("on_success", []),
        on_failure=kwargs.get("on_failure", []),
        rollback_action=kwargs.get("rollback_action", ""),
        recovery_policy_id=kwargs.get("recovery_policy_id", ""),
        required_resources=kwargs.get("required_resources", []),
        interruptible=kwargs.get("interruptible", True),
        safety_level=kwargs.get("safety_level", "normal"),
    )


def make_plan_graph_proto(**kwargs) -> types.SimpleNamespace:
    """Create a SimpleNamespace mimicking PlanGraphProto."""
    return types.SimpleNamespace(
        schema_version=kwargs.get("schema_version", "roboweave.v1"),
        plan_id=kwargs.get("plan_id", ""),
        task_id=kwargs.get("task_id", ""),
        nodes=kwargs.get("nodes", []),
        success_condition=kwargs.get(
            "success_condition",
            types.SimpleNamespace(conditions={}),
        ),
        failure_policy=kwargs.get(
            "failure_policy",
            types.SimpleNamespace(max_retry=3, fallback="ask_user_clarification"),
        ),
    )


def make_execution_event_proto(**kwargs) -> types.SimpleNamespace:
    """Create a SimpleNamespace mimicking ExecutionEventProto."""
    return types.SimpleNamespace(
        schema_version=kwargs.get("schema_version", "roboweave.v1"),
        event_id=kwargs.get("event_id", ""),
        task_id=kwargs.get("task_id", ""),
        node_id=kwargs.get("node_id", ""),
        event_type=kwargs.get("event_type", "skill_started"),
        failure_code=kwargs.get("failure_code", ""),
        severity=kwargs.get("severity", "info"),
        message=kwargs.get("message", ""),
        recovery_candidates=kwargs.get("recovery_candidates", []),
        timestamp=kwargs.get("timestamp", 0.0),
    )
