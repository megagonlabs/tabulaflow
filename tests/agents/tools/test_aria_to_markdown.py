"""Tests for the aria-YAML → markdown renderer."""

import tabulaflow.agents.tools.browser.aria as a2m
from tabulaflow.agents.tools.browser.aria import render_aria_markdown


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

    def test_plain_text_paragraph(self) -> None:
        # A prose paragraph with no inline elements arrives as a scalar body
        # (``paragraph: "..."``); its text must not be dropped.
        assert md("- paragraph [ref=e1]: Hello world, this is a bio.") == "Hello world, this is a bio."


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

    def test_multicol_table_without_columnheaders_emits_blank_header(self) -> None:
        # A multi-column table with no columnheaders (HN-style listing). The first row
        # is data, not a header, so it must stay in the body under a BLANK header row —
        # never promoted to the header (which would fabricate/duplicate a record).
        y = (
            "- table [ref=e1]:\n"
            "    - row [ref=e2]:\n"
            '        - cell "1." [ref=e3]\n'
            '        - cell "Top Story" [ref=e4]\n'
            "    - row [ref=e5]:\n"
            '        - cell "2." [ref=e6]\n'
            '        - cell "Next Story" [ref=e7]'
        )
        out = md(y)
        assert "| --- | --- |" in out
        # Blank header row precedes the separator; both data rows are in the body.
        assert "|   |   |" in out
        assert "| 1. [ref=e3] | Top Story [ref=e4] |" in out
        assert "| 2. [ref=e6] | Next Story [ref=e7] |" in out
        # The first data row is NOT the header line (nothing above the blank header).
        assert out.index("|   |   |") < out.index("| 1. [ref=e3]")

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
        # Wrapper around a single action → render the inner element only (thin
        # hit-area wrapper, redundant with its one child).
        y = '- generic [ref=e1] [cursor=pointer]:\n    - link "Deal" [ref=e2]:\n        - /url: /x'
        out = md(y)
        assert out == "[Deal](/x) [ref=e2]"

    def test_clickable_card_hoists_ref_onto_row_line(self) -> None:
        # A clickable card wrapping ≥2 distinct actions is its own affordance: its
        # ref belongs on the row line (the card IS the row), with action atoms as
        # nested bullets — not dangling as a pseudo-child of its own content.
        y = (
            "- listitem [ref=e1]:\n"
            "  - generic [ref=e2] [cursor=pointer]:\n"
            "    - generic [ref=e3]: 4:00 PM\n"
            '    - button "Details" [ref=e4]\n'
            '    - button "Emissions" [ref=e5]'
        )
        out = md(y)
        assert out.splitlines()[0] == "- 4:00 PM [ref=e2]"  # card ref on row line; span ref dropped
        assert '  - button "Details" [ref=e4]' in out
        assert "clickable" not in out  # no dangling pseudo-child handle


class TestNestedSubList:
    def test_sublist_indents_consistently_under_label(self) -> None:
        # A list nested under a labelled listitem: every sub-item indents one
        # level under the label — the first item must not de-indent to the label's
        # own level, and no spurious double-bullet ("- - item").
        y = (
            "- listitem [ref=e1]:\n"
            "  - generic [ref=e2]: Programs\n"
            "  - list [ref=e3]:\n"
            "    - listitem [ref=e4]:\n"
            '        - link "Overview" [ref=e5]:\n'
            "            - /url: /o\n"
            "    - listitem [ref=e6]:\n"
            '        - link "Tutorials" [ref=e7]:\n'
            "            - /url: /t"
        )
        out = md(y)
        # "Programs" is an informational span → no ref; the sublist links keep
        # theirs (actionable) plus their listitem record handles.
        assert out == "- Programs\n  - [Overview](/o) [ref=e5] [ref=e4]\n  - [Tutorials](/t) [ref=e7] [ref=e6]"


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


class TestInlineMarkup:
    def test_strong_and_emphasis(self) -> None:
        assert md("- strong: Title") == "**Title**"
        assert md("- emphasis: Authors") == "*Authors*"

    def test_deletion_is_strikethrough(self) -> None:
        assert md("- deletion: old") == "~~old~~"

    def test_term_definition_pair_is_regex_separable(self) -> None:
        # The title/author shape generalized: a <dl> term/definition pair stays
        # on one bullet but the term's ** delimiter keeps the boundary parseable.
        y = "- listitem [ref=e1]:\n  - term [ref=e2]: HTTP\n  - definition [ref=e3]: HyperText Transfer Protocol"
        assert md(y) == "- **HTTP** HyperText Transfer Protocol [ref=e1]"


class TestBlockquote:
    def test_blockquote_prefix(self) -> None:
        assert md("- blockquote: To be or not to be") == "> To be or not to be"


class TestRefMeansActionable:
    """``[ref=…]`` marks an actionable element only. Informational ``generic``
    spans (a flight time, an airline name) drop their ref so a ref always means
    "you can act here" and rows stay uncluttered — no field-anchor noise."""

    def test_informational_generic_spans_drop_their_ref(self) -> None:
        y = "- listitem [ref=e1]:\n  - generic [ref=e2]: Title Text\n  - generic [ref=e3]: Author One"
        out = md(y)
        # Spans merge into one readable run; their refs (e2/e3) are gone. The
        # record (listitem e1) keeps its own single handle — one ref per record.
        assert out == "- Title Text Author One [ref=e1]"
        assert "e2" not in out and "e3" not in out

    def test_clickable_row_keeps_its_single_action_ref(self) -> None:
        # A clickable card (≥2 inner actions) surfaces exactly one ref — its own
        # click affordance — not one per informational span.
        y = (
            "- listitem [ref=e1]:\n"
            "  - generic [ref=e2] [cursor=pointer]:\n"
            "    - generic [ref=e3]: 4:00 PM\n"
            "    - generic [ref=e4]: Delta\n"
            '    - button "Details" [ref=e5]\n'
            '    - button "Emissions" [ref=e6]'
        )
        out = md(y)
        assert out.splitlines()[0] == "- 4:00 PM Delta [ref=e2]"  # one row-level ref, spans dropped
        assert '  - button "Details" [ref=e5]' in out  # inner buttons stay actionable

    def test_label_derivation_stays_clean(self) -> None:
        # A generic child feeding a button/heading name must not inject its ref.
        assert md("- button [ref=e1]:\n  - generic [ref=e2]: Save") == 'button "Save" [ref=e1]'
        assert md('- heading "h" [level=2] [ref=e1]:\n  - generic [ref=e2]: Section').startswith("## Section")


class TestInteractiveAtomsNeverVanish:
    """Interactive roles must surface as a clickable atom — never fall to the
    unknown-role fallback and disappear (the menuitem/treeitem ref-loss bug)."""

    def test_menuitem_and_treeitem_keep_ref(self) -> None:
        assert md('- menuitem "Save" [ref=e9]') == 'menuitem "Save" [ref=e9]'
        assert md('- treeitem "Inbox" [ref=e9]') == 'treeitem "Inbox" [ref=e9]'

    def test_menuitemcheckbox_carries_state(self) -> None:
        assert md('- menuitemcheckbox "Wrap" [checked] [ref=e9]') == 'menuitemcheckbox "Wrap" [checked] [ref=e9]'

    def test_every_interactive_role_with_ref_renders_nonempty(self) -> None:
        for role in a2m._INTERACTIVE_ROLES:
            out = md(f'- {role} "Label" [ref=e1]')
            assert "e1" in out, f"interactive role {role!r} lost its ref: {out!r}"


class TestRoleCoverage:
    # The complete set of concrete (non-abstract) ARIA roles Playwright can emit
    # in an aria snapshot — extracted from its role-inheritance table. Abstract
    # roles (command/composite/input/landmark/range/roletype/section/sectionhead/
    # select/structure/widget/window) are excluded: ARIA forbids them as a
    # computed role, so they never appear. This is the contract the renderer must
    # cover exhaustively; a new Playwright role must be classified, not dropped.
    ALL_ARIA_ROLES = frozenset(
        """alert alertdialog application article banner blockquote button caption cell checkbox
        code columnheader combobox complementary contentinfo definition deletion dialog directory
        document emphasis feed figure form generic grid gridcell group heading img insertion link
        list listbox listitem log main marquee math menu menubar menuitem menuitemcheckbox
        menuitemradio meter navigation none note option paragraph presentation progressbar radio
        radiogroup region row rowgroup rowheader scrollbar search searchbox separator slider
        spinbutton status strong subscript superscript switch tab table tablist tabpanel term
        textbox time timer toolbar tooltip tree treegrid treeitem""".split()
    )

    def test_every_aria_role_has_an_explicit_disposition(self) -> None:
        explicit = (
            set(a2m._ROLE_HANDLERS)
            | a2m._TRANSPARENT_ROLES
            | a2m._LANDMARK_ROLES
            | a2m._GROUPING_ROLES
            | a2m._LAYOUT_PART_ROLES
            | a2m._FORM_CONTROL_ROLES
            | a2m._INTERACTIVE_ATOM_ROLES
            | a2m._PLAIN_TEXT_ROLES
            | set(a2m._INLINE_MARKUP)
        )
        unclassified = self.ALL_ARIA_ROLES - explicit
        assert not unclassified, (
            f"ARIA roles with no explicit disposition (would silently drop): {sorted(unclassified)}"
        )


class TestRecordRunFanout:
    """A run of ≥3 sibling record-generics (bare divs each wrapping ≥2 links) is
    a record list — each renders on its own line instead of collapsing into one
    inline run. A mere pair stays inline (usually the two halves of one record,
    not two records)."""

    @staticmethod
    def _record(a: str, b: str, base: int) -> str:
        return (
            f"  - generic [ref=e{base}]:\n"
            f'      - link "{a}" [ref=e{base + 1}]:\n'
            f"          - /url: /{a}\n"
            f'      - link "{b}" [ref=e{base + 2}]:\n'
            f"          - /url: /{b}"
        )

    def _wrap(self, n: int) -> str:
        recs = [self._record(f"A{i}", f"B{i}", 10 + i * 10) for i in range(n)]
        return "- generic [ref=e1]:\n" + "\n".join(recs)

    def test_three_records_fan_out_to_separate_lines(self) -> None:
        out = md(self._wrap(3))
        ref_lines = [ln for ln in out.splitlines() if "[ref=e" in ln]
        assert len(ref_lines) == 3
        assert all(ln.count("[ref=e") == 2 for ln in ref_lines)  # each record's 2 links on its own line

    def test_pair_stays_inline(self) -> None:
        out = md(self._wrap(2))
        ref_lines = [ln for ln in out.splitlines() if "[ref=e" in ln]
        assert len(ref_lines) == 1
        assert ref_lines[0].count("[ref=e") == 4

    def test_container_record_fans_out_its_inner_list(self) -> None:
        # A record list nested inside a container generic still fans out, even
        # under a top-level (flow=True) wrapper — BLOCK frags never merge inline.
        inner = "\n".join(self._record(f"A{i}", f"B{i}", 10 + i * 10) for i in range(3))
        yaml = "- generic [ref=e1]:\n  - generic [ref=e2]:\n" + "\n".join("    " + ln for ln in inner.splitlines())
        out = md(yaml)
        assert len([ln for ln in out.splitlines() if "[ref=e" in ln]) == 3


class TestInteractiveAtomStaysSingleLine:
    """An interactive element wrapping block content (the ubiquitous
    anchor-wrapped card) must still render as one single-line atom — the
    per-line ``[ref=eN]`` contract the snapshot/grep rely on."""

    def test_link_wrapping_heading_and_paragraph(self) -> None:
        y = (
            '- link "" [ref=e1]:\n'
            "    - /url: /card\n"
            '    - heading "Card Title" [level=3] [ref=e2]\n'
            "    - paragraph [ref=e3]: A long description."
        )
        out = md(y)
        assert "\n" not in out  # one line
        assert out.startswith("[Card Title A long description.](/card) [ref=e1]")
        assert "#" not in out  # heading markup stripped from the name

    def test_button_wrapping_blockquote(self) -> None:
        y = '- button "" [ref=e1]:\n    - blockquote [ref=e2]: quoted label'
        out = md(y)
        assert "\n" not in out
        assert out == 'button "quoted label" [ref=e1]'


class TestRenderDepthGuard:
    """Pathologically deep nesting degrades gracefully instead of raising an
    uncaught ``RecursionError`` that would fail the whole snapshot."""

    @staticmethod
    def _nested(depth: int) -> str:
        y = "".join("  " * i + f"- generic [ref=e{i}]:\n" for i in range(depth))
        return y + "  " * depth + '- link "x" [ref=e99999]:\n' + "  " * (depth + 1) + "- /url: /x"

    def test_deep_nesting_does_not_crash(self) -> None:
        for depth in (150, 400, 2000):
            out = render_aria_markdown(self._nested(depth))  # must not raise
            assert isinstance(out, str)

    def test_shallow_nesting_still_renders(self) -> None:
        out = md(self._nested(10))
        assert "[ref=e99999]" in out
