from typing import Protocol, Type


class NamedClass(Protocol):
    name: str


class Registry:
    def __init__(self, registry_name: str):
        self.registry_name = registry_name
        self._name_to_cls: dict[str, Type[NamedClass]] = {}

    def register(self, cls: Type[NamedClass]) -> Type[NamedClass]:
        if cls.name in self._name_to_cls:
            raise ValueError(f"Class {cls.name} already registered")
        self._name_to_cls[cls.name] = cls
        return cls

    def get_class(self, name: str) -> Type[NamedClass]:
        if name not in self._name_to_cls:
            raise ValueError(f"Unknown {self.registry_name} {name}, available: {self.list_names()}")
        return self._name_to_cls[name]

    def list_names(self) -> list[str]:
        return list(self._name_to_cls.keys())


agent_registry = Registry("agent")
dataset_registry = Registry("dataset")
metric_registry = Registry("metric")
