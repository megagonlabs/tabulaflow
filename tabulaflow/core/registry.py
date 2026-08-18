"""Named plugin class registry."""

from typing import ClassVar, Generic, Protocol, TypeVar


class _NamedClass(Protocol):
    name: ClassVar[str]


_T = TypeVar("_T", bound=_NamedClass)


class ClassRegistry(Generic[_T]):
    """Registry of plugin classes keyed by their class-level ``name``."""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._classes: dict[str, type[_T]] = {}

    def register(self, cls: type[_T]) -> type[_T]:
        if cls.name in self._classes:
            raise ValueError(f"{self._kind} {cls.name!r} is already registered")
        self._classes[cls.name] = cls
        return cls

    def get_class(self, name: str) -> type[_T]:
        try:
            return self._classes[name]
        except KeyError:
            available = ", ".join(self.list_names()) or "(none)"
            raise ValueError(f"unknown {self._kind} {name!r}; available: {available}") from None

    def list_names(self) -> list[str]:
        return list(self._classes)
