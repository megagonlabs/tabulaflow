from typing import Protocol, Type, TypeVar, Generic, ClassVar


class NamedClass(Protocol):
    name: ClassVar[str]


T = TypeVar("T", bound=NamedClass)


class Registry(Generic[T]):
    def __init__(self, registry_name: str):
        self.registry_name = registry_name
        self._name_to_cls: dict[str, Type[T]] = {}

    def register(self, cls: Type[T]) -> Type[T]:
        if cls.name in self._name_to_cls:
            raise ValueError(f"Class {cls.name} already registered")
        self._name_to_cls[cls.name] = cls
        return cls

    def get_class(self, name: str) -> Type[T]:
        if name not in self._name_to_cls:
            raise ValueError(f"Unknown {self.registry_name} {name}, available: {self.list_names()}")
        return self._name_to_cls[name]

    def list_names(self) -> list[str]:
        return list(self._name_to_cls.keys())


# agent_registry: Registry[NL2QAgent] = Registry("agent")
# dataset_registry: Registry[NL2QDatasetLoader] = Registry("dataset")
# metric_registry: Registry[NL2QMetric] = Registry("metric")
# formatter_registry: Registry[NL2QFormatter] = Registry("formatter")
