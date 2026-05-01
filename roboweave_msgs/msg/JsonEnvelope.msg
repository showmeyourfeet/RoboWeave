# Name of the schema being transported (e.g. "WorldState", "SkillCall")
string schema_name

# Schema version (e.g. "roboweave.v1")
string schema_version

# Serialized JSON payload
string payload_json

# SHA-256 hex digest of payload_json (empty string if not computed)
string payload_hash
