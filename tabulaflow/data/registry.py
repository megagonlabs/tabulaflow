"""Core registry for live database connectors."""

from __future__ import annotations
from dataclasses import dataclass, field
from tabulaflow.data.base import DataConnector


@dataclass
class DBRegistry:
    """Store named database connectors for a runtime."""

    _connectors: dict[str, DataConnector] = field(default_factory=dict)

    def has(self, alias: str) -> bool:
        """Return whether a connector is registered for ``alias``."""
        return alias in self._connectors

    def get(self, alias: str) -> DataConnector:
        """Return the connector registered for ``alias``.

        Args:
            alias: The connector alias.

        Raises:
            ValueError: If ``alias`` is not registered.
        """
        connector = self._connectors.get(alias)
        if connector is None:
            raise ValueError(f"Unknown database alias: {alias}")
        return connector

    def register(self, alias: str, connector: DataConnector) -> None:
        """Register a connector under ``alias``.

        Args:
            alias: The connector alias.
            connector: The connector instance to store.

        Raises:
            ValueError: If ``alias`` is already registered.
        """
        if alias in self._connectors:
            raise ValueError(f"Database alias already registered: {alias}")
        self._connectors[alias] = connector

    async def unregister_async(self, alias: str) -> bool:
        """Remove and disconnect the connector registered for ``alias``."""
        connector = self._connectors.pop(alias, None)
        if connector is None:
            return False
        await connector.disconnect_async()
        return True

    def list_aliases(self) -> list[str]:
        """Return the registered connector aliases."""
        return list(self._connectors.keys())

    async def disconnect_all_async(self) -> None:
        """Disconnect all registered connectors and clear the registry."""
        for connector in self._connectors.values():
            await connector.disconnect_async()
        self._connectors.clear()
