"""Tests for the aria-YAML → markdown renderer."""

from mintq.toolhub.aria_to_markdown import render_aria_markdown


def md(yaml: str) -> str:
    return render_aria_markdown(yaml).strip()


class TestHeadingsAndProse:
    def test_heading_levels(self) -> None:
        assert md('- heading "Hello" [level=1] [ref=e1]').startswith("# Hello")
        assert md('- heading "Sub" [level=3] [ref=e2]').startswith("### Sub")

    def test_paragraph_with_inline_link(self) -> None:
        y = (
            "- paragraph [ref=e1]:\n"
            '    - text: "Read the "\n'
            '    - link "docs" [ref=e2]:\n'
            "        - /url: /docs\n"
            '    - text: "."'
        )
        assert md(y) == "Read the [docs](/docs) [ref=e2]."


class TestLinksAndButtons:
    def test_link_inlines_href_and_ref(self) -> None:
        y = '- link "Click me" [ref=e1]:\n    - /url: /x'
        assert md(y) == "[Click me](/x) [ref=e1]"

    def test_link_without_href(self) -> None:
        assert md('- link "X" [ref=e1]') == "[X] [ref=e1]"

    def test_button_inlines_ref(self) -> None:
        assert md('- button "Submit" [ref=e1]') == 'button "Submit" [ref=e1]'

    def test_button_disabled_state_not_in_markdown(self) -> None:
        # State flags surface via the interactive-elements list, not in the md.
        assert md('- button "Go" [disabled] [ref=e1]') == 'button "Go" [ref=e1]'

    def test_button_without_name(self) -> None:
        assert md("- button [ref=e1]") == "button [ref=e1]"


class TestBlockAtomsInListitems:
    def test_heading_in_listitem_does_not_combine_with_text(self) -> None:
        # A heading should not get joined into a plain-text run with siblings,
        # even when both lack refs.
        y = (
            "- list [ref=e0]:\n"
            "    - listitem [ref=e1]:\n"
            '        - text: "before"\n'
            '        - heading "Section" [level=3] [ref=e2]\n'
            '        - text: "after"'
        )
        out = md(y)
        # The heading marker must remain on its own line, not get spliced into
        # ``before ### Section after``.
        assert "### Section" in out
        assert "before ### Section after" not in out


class TestLists:
    def test_unordered(self) -> None:
        y = (
            "- list [ref=e0]:\n"
            "    - listitem [ref=e1]:\n"
            '        - text: "alpha"\n'
            "    - listitem [ref=e2]:\n"
            '        - text: "beta"'
        )
        out = md(y)
        assert "- alpha" in out
        assert "- beta" in out


class TestTables:
    def test_data_table_renders_as_pipe_table(self) -> None:
        y = (
            "- table [ref=e1]:\n"
            "    - row [ref=e2]:\n"
            '        - columnheader "Name" [ref=e3]\n'
            '        - columnheader "Score" [ref=e4]\n'
            "    - row [ref=e5]:\n"
            '        - cell "Alice" [ref=e6]\n'
            '        - cell "10" [ref=e7]\n'
            "    - row [ref=e8]:\n"
            '        - cell "Bob" [ref=e9]\n'
            '        - cell "12" [ref=e10]'
        )
        out = md(y)
        assert "| Name [ref=e3] | Score [ref=e4] |" in out
        assert "| --- | --- |" in out
        assert "| Alice [ref=e6] | 10 [ref=e7] |" in out

    def test_layout_table_renders_transparently(self) -> None:
        # Single-column "table" (HN-style layout). Should NOT produce pipes.
        y = (
            "- table [ref=e1]:\n"
            "    - row [ref=e2]:\n"
            '        - cell [ref=e3]:\n'
            '            - text: "headline"\n'
            "    - row [ref=e4]:\n"
            '        - cell [ref=e5]:\n'
            '            - text: "body"'
        )
        out = md(y)
        assert "|" not in out
        assert "headline" in out and "body" in out


class TestFormControls:
    def test_textbox_inlines_value(self) -> None:
        assert md('- textbox "Where from" [ref=e1]: SFO') == (
            'textbox "Where from" = "SFO" [ref=e1]'
        )

    def test_combobox_with_state(self) -> None:
        assert md('- combobox "menu" [expanded] [ref=e1]: One way') == (
            'combobox "menu" = "One way" [expanded] [ref=e1]'
        )

    def test_checkbox_state(self) -> None:
        out = md('- checkbox "Nonstop" [checked] [ref=e1]')
        assert out == 'checkbox "Nonstop" [checked] [ref=e1]'


class TestClickableGeneric:
    def test_leaf_clickable_generic_inlined_as_button(self) -> None:
        # Pill-style div: cursor=pointer, no interactive descendants.
        out = md('- generic [ref=e1] [cursor=pointer]: May 23')
        assert out == 'clickable "May 23" [ref=e1]'

    def test_wrapper_clickable_generic_does_not_inline_itself(self) -> None:
        # Wrapper around a link → render the inner link only.
        y = (
            "- generic [ref=e1] [cursor=pointer]:\n"
            '    - link "Deal" [ref=e2]:\n'
            "        - /url: /x"
        )
        out = md(y)
        assert out == "[Deal](/x) [ref=e2]"


class TestRobustness:
    def test_yaml_special_scalar_does_not_break(self) -> None:
        # ``=`` and ``~`` would error under SafeLoader; BaseLoader keeps them strings.
        assert "=" in md('- generic [ref=e1]: =')
        assert "~" in md('- generic [ref=e2]: ~')

    def test_empty_input(self) -> None:
        assert render_aria_markdown("") == ""

    def test_malformed_yaml_returns_empty(self) -> None:
        # No fallback for the renderer — fail-soft to empty string.
        assert render_aria_markdown('- button "x" [ref=e1]: "unclosed\n') == ""
