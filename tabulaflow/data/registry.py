"""Registry for live data connectors."""

from __future__ import annotations

from tabulaflow.data.protocols import DataConnector, validate_global_id


class DataConnectorRegistry:
    """Store named data connectors for a runtime."""

    def __init__(self) -> None:
        self._connectors: dict[str, DataConnector] = {}

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
            raise ValueError(f"Unknown connector alias: {alias}")
        return connector

    def register(self, alias: str, connector: DataConnector) -> None:
        """Register a connector under ``alias``.

        Args:
            alias: The connector alias.
            connector: The connector instance to store.

        Raises:
            ValueError: If ``alias`` is already registered.
        """
        validate_global_id(connector.global_id)
        if alias in self._connectors:
            raise ValueError(f"Connector alias already registered: {alias}")
        self._connectors[alias] = connector

    async def close_async(self, alias: str) -> bool:
        """Remove and close the connector registered for ``alias``."""
        connector = self._connectors.pop(alias, None)
        if connector is None:
            return False
        await connector.close_async()
        return True

    def list_aliases(self) -> list[str]:
        """Return the registered connector aliases."""
        return list(self._connectors.keys())

    async def close_all_async(self) -> None:
        """Close all registered connectors and clear the registry."""
        for connector in self._connectors.values():
            await connector.close_async()
        self._connectors.clear()
