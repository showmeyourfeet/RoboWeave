from __future__ import annotations

import hashlib

import pydantic

from ._version import SCHEMA_VERSION


class VersionedModel(pydantic.BaseModel):
    """Base class for all cross-process data structures carrying a schema version."""

    schema_version: str = SCHEMA_VERSION


class TimestampedData(VersionedModel):
    """Base class for time-sensitive data with temporal metadata."""

    timestamp: float = 0.0
    frame_id: str = ""
    valid_until: float = 0.0  # 0 = no expiry
    source_module: str = ""
    confidence: float = 1.0


class JsonEnvelope(pydantic.BaseModel):
    """Uniform JSON transport wrapper with integrity hashing."""

    schema_name: str
    schema_version: str
    payload_json: str
    payload_hash: str = ""

    @classmethod
    def wrap(cls, model: VersionedModel) -> JsonEnvelope:
        """Serialize a VersionedModel into a JsonEnvelope with SHA-256 hash."""
        json_str = model.model_dump_json()
        hash_hex = hashlib.sha256(json_str.encode()).hexdigest()
        return cls(
            schema_name=type(model).__name__,
            schema_version=model.schema_version,
            payload_json=json_str,
            payload_hash=hash_hex,
        )
