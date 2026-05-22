"""Tests for parsing Playwright aria snapshots into interactive elements."""

from mintq.toolhub.web_browser import (
    InteractiveElement,
    parse_interactive_elements,
    render_interactive_elements,
)


def _by_ref(elements: list[InteractiveElement]) -> dict[str, InteractiveElement]:
    return {e.ref: e for e in elements}


class TestParseBasics:
    def test_role_name_ref(self) -> None:
        els = parse_interactive_elements('- button "Search" [ref=e1]')
        assert els == [InteractiveElement(ref="e1", role="button", name="Search")]

    def test_non_interactive_roles_dropped(self) -> None:
        # headings/generics are not interactive; only the button comes through.
        yaml = '- heading "Title" [ref=e1]\n- button "Go" [ref=e2]'
        els = parse_interactive_elements(yaml)
        assert [e.ref for e in els] == ["e2"]

    def test_refless_nodes_dropped(self) -> None:
        # A bare option with no ref is not independently interactable.
        assert parse_interactive_elements('- option "One way"') == []


class TestStateAndValue:
    def test_value(self) -> None:
        (el,) = parse_interactive_elements('- textbox "Where from" [ref=e1]: San Francisco')
        assert el.value == "San Francisco"

    def test_quoted_numeric_value(self) -> None:
        (el,) = parse_interactive_elements('- slider "price" [ref=e1]: "40"')
        assert el.value == "40"

    def test_state_flags(self) -> None:
        yaml = (
            '- checkbox "Nonstop" [checked] [ref=e1]\n'
            '- button "Search" [disabled] [ref=e2]\n'
            '- button "Bold" [pressed] [ref=e3]'
        )
        by = _by_ref(parse_interactive_elements(yaml))
        assert by["e1"].state == ("checked",)
        assert by["e2"].state == ("disabled",)
        assert by["e3"].state == ("pressed",)

    def test_expanded_combobox_keeps_value_and_state(self) -> None:
        (el,) = parse_interactive_elements('- combobox "menu" [expanded] [ref=e1]: Round trip')
        assert el.value == "Round trip"
        assert el.state == ("expanded",)
        assert el.native_select is False


class TestLinks:
    def test_href_from_url_child(self) -> None:
        yaml = '- link "Deals" [ref=e1]:\n    - /url: /deals'
        (el,) = parse_interactive_elements(yaml)
        assert el.href == "/deals"


class TestNativeSelect:
    def test_native_select_detected_with_options(self) -> None:
        yaml = (
            '- combobox "ticket" [ref=e1]:\n'
            '    - option "One way"\n'
            '    - option "Round trip" [selected]'
        )
        (el,) = parse_interactive_elements(yaml)
        assert el.native_select is True
        assert el.native_options == ("One way", "Round trip")

    def test_options_through_optgroup(self) -> None:
        yaml = (
            '- combobox "ticket" [ref=e1]:\n'
            '    - group "G":\n'
            '        - option "A"\n'
            '        - option "B"'
        )
        (el,) = parse_interactive_elements(yaml)
        assert el.native_select is True
        assert el.native_options == ("A", "B")

    def test_options_capped(self) -> None:
        opts = "\n".join(f'    - option "City {i}"' for i in range(25))
        (el,) = parse_interactive_elements(f'- combobox "city" [ref=e1]:\n{opts}')
        assert el.native_select is True
        assert len(el.native_options) == 15  # _MAX_NATIVE_OPTIONS

    def test_aria_combobox_with_refd_options_not_native(self) -> None:
        # An expanded ARIA combobox's options carry refs ⇒ not a native select.
        yaml = (
            '- combobox "menu" [expanded] [ref=e1]\n'
            "- listbox [ref=e2]:\n"
            '    - option "A" [ref=e3]\n'
            '    - option "B" [ref=e4]'
        )
        by = _by_ref(parse_interactive_elements(yaml))
        assert by["e1"].native_select is False
        assert by["e3"].role == "option"  # listbox options surface with their refs


class TestContext:
    def test_sibling_heading_is_context(self) -> None:
        yaml = '- heading "Filters" [ref=e1]\n- button "Stops" [ref=e2]'
        by = _by_ref(parse_interactive_elements(yaml))
        assert by["e2"].parent_context == ("heading", "Filters")

    def test_deeper_context_does_not_leak_to_shallower(self) -> None:
        # A context node nested deeper than a following element is popped, so it
        # doesn't leak; a same-depth context node remains in scope (matches the
        # original indent-based "<= depth" rule).
        yaml = (
            '- region "R" [ref=e1]:\n'
            '    - listitem "Item":\n'
            '        - button "B1" [ref=e2]\n'
            '- button "B2" [ref=e3]'
        )
        by = _by_ref(parse_interactive_elements(yaml))
        assert by["e2"].parent_context == ("listitem", "Item")  # nearest, deepest
        assert by["e3"].parent_context == ("region", "R")  # listitem popped, region kept


class TestFallback:
    def test_malformed_yaml_recovers_refs(self) -> None:
        # Unbalanced quote breaks YAML; fallback still extracts the ref line.
        els = parse_interactive_elements('- button "Go" [ref=e9]: "x\n')
        assert els == [InteractiveElement(ref="e9", role="button", name="Go")]

    def test_empty_input(self) -> None:
        assert parse_interactive_elements("") == []


class TestRender:
    def test_render_combines_value_state_context(self) -> None:
        yaml = '- heading "Filters" [ref=e0]\n- textbox "From" [ref=e1]: SFO'
        out = render_interactive_elements(parse_interactive_elements(yaml))
        assert out == '- [ref=e1] textbox "From" = "SFO" (under: heading "Filters")'
