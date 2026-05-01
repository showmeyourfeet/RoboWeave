"""BackendRegistry - Plugin system for planning backends.

Backends register themselves via the @register_backend decorator at import time.
The registry validates that each class implements the correct ABC.
"""

from __future__ import annotations

from typing import Type

from .grasp_planner import GraspPlanner
from .ik_solver import IKSolver
from .collision_checker import CollisionChecker
from .motion_planner import MotionPlanner

# Capability constants
GRASP_PLANNER = "grasp_planner"
IK_SOLVER = "ik_solver"
COLLISION_CHECKER = "collision_checker"
MOTION_PLANNER = "motion_planner"

# Capability name → required ABC
_ABC_MAP: dict[str, Type] = {
    GRASP_PLANNER: GraspPlanner,
    IK_SOLVER: IKSolver,
    COLLISION_CHECKER: CollisionChecker,
    MOTION_PLANNER: MotionPlanner,
}

# Capability name → { backend_name → class }
_REGISTRY: dict[str, dict[str, Type]] = {
    GRASP_PLANNER: {},
    IK_SOLVER: {},
    COLLISION_CHECKER: {},
    MOTION_PLANNER: {},
}


def register_backend(capability: str, name: str):
    """Decorator to register a backend class for a capability.

    Usage:
        @register_backend("grasp_planner", "mock")
        class MockGraspPlanner(GraspPlanner):
            ...
    """
    def decorator(cls: Type) -> Type:
        abc_cls = _ABC_MAP.get(capability)
        if abc_cls and not issubclass(cls, abc_cls):
            raise TypeError(
                f"{cls.__name__} does not implement {abc_cls.__name__}"
            )
        _REGISTRY[capability][name] = cls
        return cls
    return decorator


def get_backend(capability: str, name: str, **kwargs):
    """Instantiate a backend by capability and name.

    Raises:
        KeyError: If the backend name is not registered.
    """
    backends = _REGISTRY.get(capability, {})
    if name not in backends:
        available = list(backends.keys())
        raise KeyError(
            f"Backend '{name}' not found for '{capability}'. "
            f"Available: {available}"
        )
    return backends[name](**kwargs)


def list_backends(capability: str) -> list[str]:
    """List registered backend names for a capability."""
    return list(_REGISTRY.get(capability, {}).keys())
