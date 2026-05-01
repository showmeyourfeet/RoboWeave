from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .base import VersionedModel
from .refs import ImageRef


class HITLRequestType(str, Enum):
    """Type of human-in-the-loop request."""

    CONFIRM_TARGET = "confirm_target"
    DISAMBIGUATE_TARGET = "disambiguate_target"
    CONFIRM_ACTION = "confirm_action"
    TELEOP_ASSIST = "teleop_assist"
    MANUAL_CORRECTION = "manual_correction"
    SAFETY_RELEASE = "safety_release"


class HITLRequest(VersionedModel):
    """A request for human-in-the-loop intervention."""

    request_id: str
    task_id: str
    request_type: HITLRequestType
    message: str
    options: list[str] = Field(default_factory=list)
    image_refs: list[ImageRef] = Field(default_factory=list)
    timeout_sec: float = 60.0
    priority: str = "normal"


class HITLResponse(VersionedModel):
    """Response from a human operator."""

    request_id: str
    response_type: str = ""
    selected_option: str = ""
    text_input: str = ""
    click_point: list[float] = Field(default_factory=list)
    correction_data: dict[str, Any] = Field(default_factory=dict)
    operator_id: str = ""
