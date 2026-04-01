"""Database connection manager for the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field

from mintq.db_connector.base import NL2QDBConnector


@dataclass
class ConnectionManager:
    """Tracks multiple named database connections."""

    _connections: dict[str, NL2QDBConnector] = field(default_factory=dict)
    _active: str | None = None

    @property
    def active_alias(self) -> str | None:
        return self._active

    @property
    def active_connector(self) -> NL2QDBConnector | None:
        if self._active is None:
            return None
        return self._connections.get(self._active)

    def has(self, alias: str) -> bool:
        return alias in self._connections

    def add(self, alias: str, connector: NL2QDBConnector) -> None:
        self._connections[alias] = connector
        if self._active is None:
            self._active = alias

    async def remove(self, alias: str) -> bool:
        connector = self._connections.pop(alias, None)
        if connector is None:
            return False
        await connector.disconnect_async()
        if self._active == alias:
            self._active = next(iter(self._connections), None)
        return True

    def use(self, alias: str) -> bool:
        if alias not in self._connections:
            return False
        self._active = alias
        return True

    def list_all(self) -> dict[str, NL2QDBConnector]:
        return dict(self._connections)

    async def disconnect_all(self) -> None:
        for connector in self._connections.values():
            await connector.disconnect_async()
        self._connections.clear()
        self._active = None
