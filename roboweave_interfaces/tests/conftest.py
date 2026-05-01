"""Shared test fixtures and helpers for roboweave_interfaces tests."""

from __future__ import annotations

import pytest

# Import all modules to ensure all subclasses are registered
import roboweave_interfaces  # noqa: F401


def discover_versioned_models():
    """Recursively discover all VersionedModel subclasses."""
    from roboweave_interfaces.base import VersionedModel

    result = []
    queue = list(VersionedModel.__subclasses__())
    while queue:
        cls = queue.pop()
        result.append(cls)
        queue.extend(cls.__subclasses__())
    return result


@pytest.fixture
def all_versioned_model_classes():
    """Fixture providing all VersionedModel subclasses."""
    return discover_versioned_models()
