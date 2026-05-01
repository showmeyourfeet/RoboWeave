"""ResourceManager — shared/exclusive resource lock management."""

from __future__ import annotations


class ResourceManager:
    """Pure Python resource lock manager with atomic all-or-nothing semantics."""

    def __init__(self) -> None:
        # resource_name -> set of holders sharing it
        self._shared: dict[str, set[str]] = {}
        # resource_name -> exclusive holder (or None)
        self._exclusive: dict[str, str | None] = {}

    def acquire(
        self, holder: str, shared: list[str], exclusive: list[str]
    ) -> tuple[bool, str]:
        """
        Attempt to acquire resources atomically.
        Returns (success, conflict_message).
        """
        # Check all resources for conflicts before acquiring any
        for resource in exclusive:
            if not self._can_acquire_exclusive(resource, holder):
                holders = self.get_holders(resource)
                return (
                    False,
                    f"Exclusive conflict on '{resource}': held by {holders}",
                )

        for resource in shared:
            if not self._can_acquire_shared(resource, holder):
                exc_holder = self._exclusive.get(resource)
                return (
                    False,
                    f"Shared conflict on '{resource}': exclusively held by '{exc_holder}'",
                )

        # All checks passed — acquire atomically
        for resource in exclusive:
            self._exclusive[resource] = holder
        for resource in shared:
            if resource not in self._shared:
                self._shared[resource] = set()
            self._shared[resource].add(holder)

        return True, "Acquired"

    def release(self, holder: str) -> None:
        """Release all resources held by the given holder."""
        # Release exclusive
        to_remove = [r for r, h in self._exclusive.items() if h == holder]
        for r in to_remove:
            self._exclusive[r] = None

        # Release shared
        for resource, holders in self._shared.items():
            holders.discard(holder)

    def is_available(self, resource: str, exclusive: bool = False) -> bool:
        """Check if a resource is available for the requested access mode."""
        if exclusive:
            return self._can_acquire_exclusive(resource, "")
        return self._can_acquire_shared(resource, "")

    def get_holders(self, resource: str) -> list[str]:
        """Return list of current holders of a resource."""
        holders: list[str] = []
        exc = self._exclusive.get(resource)
        if exc is not None:
            holders.append(exc)
        shared = self._shared.get(resource, set())
        holders.extend(sorted(shared))
        return holders

    # --- Internal helpers ---

    def _can_acquire_exclusive(self, resource: str, holder: str) -> bool:
        """Check if exclusive acquisition is possible."""
        # Blocked if someone else holds it exclusively
        exc = self._exclusive.get(resource)
        if exc is not None and exc != holder:
            return False
        # Blocked if anyone holds it shared (other than the requester)
        shared = self._shared.get(resource, set())
        other_shared = shared - {holder}
        if other_shared:
            return False
        return True

    def _can_acquire_shared(self, resource: str, holder: str) -> bool:
        """Check if shared acquisition is possible."""
        # Blocked if someone else holds it exclusively
        exc = self._exclusive.get(resource)
        if exc is not None and exc != holder:
            return False
        return True
