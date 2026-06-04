"""Tests for the aria-YAML → markdown renderer."""

from tabulaflow.toolhub.aria_to_markdown import render_aria_markdown


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
            "        - cell [ref=e3]:\n"
            '            - text: "headline"\n'
            "    - row [ref=e4]:\n"
            "        - cell [ref=e5]:\n"
            '            - text: "body"'
        )
        out = md(y)
        assert "|" not in out
        assert "headline" in out and "body" in out


class TestFormControls:
    def test_textbox_inlines_value(self) -> None:
        assert md('- textbox "Where from" [ref=e1]: SFO') == ('textbox "Where from" = "SFO" [ref=e1]')

    def test_combobox_with_state(self) -> None:
        assert md('- combobox "menu" [expanded] [ref=e1]: One way') == (
            'combobox "menu" = "One way" [expanded] [ref=e1]'
        )

    def test_checkbox_state(self) -> None:
        out = md('- checkbox "Nonstop" [checked] [ref=e1]')
        assert out == 'checkbox "Nonstop" [checked] [ref=e1]'

    def test_bare_textual_input_is_dropped(self) -> None:
        # No name + no value + no interactive descendants → drop. The agent
        # can't safely target it; screen readers also skip these (WCAG 3.3.2).
        assert md("- textbox [ref=e1]") == ""
        assert md("- combobox [ref=e2]") == ""
        assert md("- searchbox [ref=e3]") == ""
        assert md("- spinbutton [ref=e4]") == ""

    def test_value_bearing_textual_input_is_kept(self) -> None:
        # Value gives semantic info even when name is missing; keep.
        assert md("- combobox [ref=e1]: Economy") == 'combobox = "Economy" [ref=e1]'

    def test_named_bare_textual_input_is_kept(self) -> None:
        # Name without value is still useful; keep.
        assert md('- textbox "Search" [ref=e1]') == 'textbox "Search" [ref=e1]'

    def test_bare_checkbox_is_kept(self) -> None:
        # State (checked/unchecked) is meaningful even without a name.
        assert md("- checkbox [ref=e1]") == "checkbox [ref=e1]"

    def test_expanded_bare_combobox_with_options_is_kept(self) -> None:
        # Interactive descendants mean it's an active popup — keep + bullet.
        y = '- combobox [ref=e1]:\n    - option "A" [ref=e2]\n    - option "B" [ref=e3]'
        out = md(y)
        assert "combobox [ref=e1]" in out
        assert '- option "A" [ref=e2]' in out

    def test_expanded_combobox_with_nested_options(self) -> None:
        # Google-Flights pattern: options nested inside the combobox rather
        # than in a sibling listbox. Must render as a header + sub-list, not
        # crammed into the ``= "value"`` slot with nested quotes.
        y = (
            '- combobox "Where to?" [expanded] [ref=e1]:\n'
            '    - option "Anywhere" [ref=e2]\n'
            '    - option "Europe" [ref=e3]\n'
            '    - button "Toggle" [ref=e4]'
        )
        out = md(y)
        assert '= "' not in out  # no value-slot mash
        assert 'combobox "Where to?" [expanded] [ref=e1]' in out
        assert '- option "Anywhere" [ref=e2]' in out
        assert '- option "Europe" [ref=e3]' in out
        assert '- button "Toggle" [ref=e4]' in out

    def test_textbox_with_interactive_children_promotes_to_sublist(self) -> None:
        # Autocomplete textbox carrying a child suggestion listbox — same
        # cramming bug class as expanded combobox; same fix.
        y = '- textbox "Search" [ref=e1]:\n    - option "First" [ref=e2]\n    - option "Second" [ref=e3]'
        out = md(y)
        assert '= "' not in out
        assert 'textbox "Search" [ref=e1]' in out
        assert '- option "First" [ref=e2]' in out
        assert '- option "Second" [ref=e3]' in out

    def test_expanded_combobox_unwraps_transparent_listbox(self) -> None:
        # Real shape: combobox > generic/listbox wrapper > options. The wrapper
        # must be flattened so each option bullets individually instead of
        # collapsing into one inline run.
        y = (
            '- combobox "Where to?" [expanded] [ref=e1]:\n'
            "    - generic [ref=e2]:\n"
            '        - option "Anywhere" [ref=e3]\n'
            '        - option "Europe" [ref=e4]\n'
            '        - option "Paris" [ref=e5]'
        )
        out = md(y)
        assert '- option "Anywhere" [ref=e3]' in out
        assert '- option "Europe" [ref=e4]' in out
        assert '- option "Paris" [ref=e5]' in out

    def test_presentation_wrapper_is_transparent(self) -> None:
        # ARIA ``presentation``/``none`` mean "treat as if absent." A trailing
        # presentation wrapper inside a form control (Google Flights pattern)
        # must let its children surface as their own bullets, not crammed
        # together via the unknown-role inline-flow fallback.
        y = (
            '- combobox "Where to?" [expanded] [ref=e1]:\n'
            '    - option "Anywhere" [ref=e2]\n'
            "    - presentation [ref=e3]:\n"
            '        - text: "Label"\n'
            '        - button "Action" [ref=e4]'
        )
        out = md(y)
        assert '- option "Anywhere" [ref=e2]' in out
        assert '- button "Action" [ref=e4]' in out
        for line in out.splitlines():
            assert line.count("[ref=") <= 1, f"crammed: {line!r}"

    def test_expanded_combobox_with_listbox_wrapper(self) -> None:
        # Google-Flights shape: combobox > listbox > options + interleaved
        # buttons + text labels. The ``listbox`` wrapper is in
        # _TRANSPARENT_ROLES so _flatten_to_leaves drills through it; each
        # interactive atom (option/button) gets its own bullet.
        y = (
            '- combobox "Where to?" [expanded] [ref=e1]:\n'
            "    - listbox [ref=e2]:\n"
            '        - option "Anywhere" [ref=e3]\n'
            '        - option "Paris" [ref=e4]\n'
            '        - button "Toggle nearby" [ref=e5]\n'
            '        - option "London" [ref=e6]'
        )
        out = md(y)
        assert '- option "Anywhere" [ref=e3]' in out
        assert '- option "Paris" [ref=e4]' in out
        assert '- button "Toggle nearby" [ref=e5]' in out
        assert '- option "London" [ref=e6]' in out


class TestClickableGeneric:
    def test_leaf_clickable_generic_inlined_as_button(self) -> None:
        # Pill-style div: cursor=pointer, no interactive descendants.
        out = md("- generic [ref=e1] [cursor=pointer]: May 23")
        assert out == 'clickable "May 23" [ref=e1]'

    def test_wrapper_clickable_generic_does_not_inline_itself(self) -> None:
        # Wrapper around a link → render the inner link only.
        y = '- generic [ref=e1] [cursor=pointer]:\n    - link "Deal" [ref=e2]:\n        - /url: /x'
        out = md(y)
        assert out == "[Deal](/x) [ref=e2]"


class TestRobustness:
    def test_yaml_special_scalar_does_not_break(self) -> None:
        # ``=`` and ``~`` would error under SafeLoader; BaseLoader keeps them strings.
        assert "=" in md("- generic [ref=e1]: =")
        assert "~" in md("- generic [ref=e2]: ~")

    def test_empty_input(self) -> None:
        assert render_aria_markdown("") == ""

    def test_malformed_yaml_returns_empty(self) -> None:
        # No fallback for the renderer — fail-soft to empty string.
        assert render_aria_markdown('- button "x" [ref=e1]: "unclosed\n') == ""
