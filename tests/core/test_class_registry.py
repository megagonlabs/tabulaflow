from typing import ClassVar, Protocol

import pytest

from tabulaflow.core import ClassRegistry


class Plugin(Protocol):
    name: ClassVar[str]


def test_register_returns_class_and_preserves_order() -> None:
    registry = ClassRegistry[Plugin]("plugin")

    @registry.register
    class First:
        name: ClassVar[str] = "first"

    @registry.register
    class Second:
        name: ClassVar[str] = "second"

    assert registry.get_class("first") is First
    assert registry.get_class("second") is Second
    assert registry.list_names() == ["first", "second"]


def test_rejects_duplicate_name() -> None:
    registry = ClassRegistry[Plugin]("plugin")

    class First:
        name: ClassVar[str] = "same"

    class Duplicate:
        name: ClassVar[str] = "same"

    registry.register(First)
    with pytest.raises(ValueError, match="plugin 'same' is already registered"):
        registry.register(Duplicate)


def test_unknown_name_lists_available_classes() -> None:
    registry = ClassRegistry[Plugin]("plugin")

    with pytest.raises(ValueError, match=r"unknown plugin 'missing'; available: \(none\)"):
        registry.get_class("missing")

    @registry.register
    class First:
        name: ClassVar[str] = "first"

    @registry.register
    class Second:
        name: ClassVar[str] = "second"

    with pytest.raises(ValueError, match="unknown plugin 'missing'; available: first, second"):
        registry.get_class("missing")
