"""Connected-source schema explorer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from tabulaflow.app.tui.theme import (
    ERROR,
    FK_MARKER,
    KEY_HINT,
    PK_MARKER,
)
from tabulaflow.app.tui.screens.results import DataBrowserScreen

_NODE_KIND_SOURCE = "source"
_NODE_KIND_SCHEMA = "schema"
_NODE_KIND_TABLE = "table"
_NODE_KIND_COLUMN = "column"
_NODE_KIND_GRAPH_GROUP = "graph_group"
_NODE_KIND_GRAPH_NODE = "graph_node"
_NODE_KIND_GRAPH_RELATIONSHIP = "graph_relationship"
_NODE_KIND_GRAPH_PROPERTY = "graph_property"

_GRAPH_NODE_TYPES = "node_types"
_GRAPH_REL_TYPES = "relationship_types"
_GRAPH_GROUP_LABELS = {
    _GRAPH_NODE_TYPES: "Node Types",
    _GRAPH_REL_TYPES: "Relationship Types",
}


if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from tabulaflow.data.registry import DataConnectorRegistry
    from tabulaflow.data.protocols import DataConnector


class _NodeData:
    """Metadata attached to each Tree node."""

    __slots__ = ("kind", "alias", "schema_name", "table_name", "column_name", "path", "status_text")

    def __init__(
        self,
        kind: str,
        alias: str,
        schema_name: str | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
        path: tuple[str | None, ...] | None = None,
        status_text: str | None = None,
    ) -> None:
        self.kind = kind
        self.alias = alias
        self.schema_name = schema_name
        self.table_name = table_name
        self.column_name = column_name
        self.path = path
        self.status_text = status_text


_NodePath = tuple[str | None, ...]


class ExplorerState:
    """Session-scoped UI state for ``SchemaBrowserScreen``.

    Held on ``TabulaflowApp`` and passed by reference into each freshly-created
    schema browser. The screen reads ``expansion`` while building nodes
    and updates state continuously via tree event handlers — no
    snapshot-on-close step needed.

    ``expansion`` is a *dict*, not a set: presence of a path means "the
    user has seen this node," and the value is its expansion state.
    Unknown paths fall through to the build-time default. This is what
    distinguishes "user explicitly collapsed" (path → False) from "user
    never saw this node" (path absent → use default), so newly-connected
    Sources honor their auto-expand default instead of being collapsed by
    a missing entry.
    """

    __slots__ = ("expansion", "cursor")

    def __init__(self) -> None:
        self.expansion: dict[_NodePath, bool] = {}
        self.cursor: _NodePath | None = None


class SchemaBrowserScreen(Screen[None]):
    """Full-screen tree browser for exploring connected data-source schemas."""

    DEFAULT_CSS = """
    SchemaBrowserScreen {
        background: $background;
    }

    SchemaBrowserScreen #browse-tree {
        height: 1fr;
        padding: 1 2;
        background: $background;
        scrollbar-color: #666666;
        scrollbar-color-hover: #5FAF87;
        scrollbar-color-active: #5FAF87;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--cursor {
        background: #5FAF87;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree:focus {
        outline: none;
        background-tint: transparent 0%;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--cursor {
        background: #5FAF87;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight-line {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-hover {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen .schema-browser-status {
        padding: 0 2;
        color: #f5f5f5;
    }

    SchemaBrowserScreen .schema-browser-gap {
        height: 1;
    }

    SchemaBrowserScreen #browse-hint {
        dock: bottom;
        padding: 0 2;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("left", "collapse_node", "Collapse", show=False, priority=True),
        Binding("right", "expand_node", "Expand", show=False, priority=True),
        Binding("enter", "open_preview", "Preview table", show=False, priority=True),
        Binding("r", "refresh_schema", "Refresh", show=True),
    ]

    _PREVIEW_ROW_CAP = 50

    def __init__(
        self,
        *,
        registry: DataConnectorRegistry,
        alias: str | None = None,
        state: ExplorerState | None = None,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._filter_alias = alias
        self._state = state if state is not None else ExplorerState()
        self._refreshing = False
        self._status = Static(classes="schema-browser-status")
        self._gap = Static(classes="schema-browser-gap")
        self._hint = Static(id="browse-hint")

    def compose(self) -> ComposeResult:
        from textual.widgets import Tree

        tree: Tree[_NodeData] = Tree("Data sources", id="browse-tree")
        tree.show_root = False
        tree.guide_depth = 3
        tree.auto_expand = False

        yield tree
        yield self._status
        yield self._gap
        yield self._hint

    def on_mount(self) -> None:
        # Snapshot the saved cursor before any side effects can clobber it.
        # ``on_tree_node_highlighted`` rewrites ``_state.cursor`` whenever
        # the cursor moves, including the implicit move that Textual does
        # to the first line on initial render — without this local, that
        # would overwrite the path we're about to restore to.
        saved_cursor = self._state.cursor
        self._build_tree()
        self._update_status()
        self._update_hint()
        tree = self.query_one("#browse-tree")
        tree.focus()
        # Cursor restore is deferred to after the next refresh: ancestor
        # expansion (built into the tree but applied lazily by Textual)
        # only populates ``_tree_lines`` on render. Running ``move_cursor``
        # before that leaves it as a silent no-op for collapsed-by-default
        # subtrees (the workspace alias case).
        if saved_cursor is not None:
            self.call_after_refresh(self._restore_cursor, saved_cursor)
        elif not self._state.expansion:
            # Genuine first open — nothing to restore, focus the first
            # table so Enter previews immediately.
            self.call_after_refresh(self._focus_first_table)

    @staticmethod
    def _node_path(data: "_NodeData | None") -> _NodePath | None:
        if data is None:
            return None
        if data.path is not None:
            return data.path
        return (data.alias, data.schema_name, data.table_name, data.column_name)

    def _expand_for(self, path: _NodePath, default: bool) -> bool:
        """Resolve expansion state for a node: the user's last-recorded
        value if known, otherwise the construction-time default.
        """
        return self._state.expansion.get(path, default)

    def _walk_nodes(self) -> "Iterator[Any]":
        """Pre-order traversal of every tree node below the (hidden) root."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        stack: list[Any] = list(reversed(tree.root.children))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def _find_node_by_path(self, path: _NodePath) -> "Any | None":
        for node in self._walk_nodes():
            if self._node_path(node.data) == path:
                return node
        return None

    def _first_table_node(self) -> "Any | None":
        for node in self._walk_nodes():
            data: _NodeData | None = node.data
            if data is not None and data.kind == _NODE_KIND_TABLE:
                return node
        return None

    def _restore_cursor(self, saved: _NodePath | None) -> None:
        """Move the cursor to the saved node, if its path still resolves.

        Deliberately does not fall back to the first table or force
        ancestor expansion when the path is missing — the build phase
        already put the tree in the user's saved collapse state, and
        overriding that to make a fallback cursor visible would silently
        undo an explicit collapse (e.g., after a disconnect dropped the
        saved cursor's source).
        """
        if saved is None:
            return
        target = self._find_node_by_path(saved)
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    def _focus_first_table(self) -> None:
        """First-open default: land the cursor on the first table so Enter
        previews immediately. Force-expands ancestors because on a true
        first open there is no user-intended collapse state to respect.
        """
        target = self._first_table_node()
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        parent = target.parent
        while parent is not None and parent is not tree.root:
            parent.expand()
            parent = parent.parent
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    def on_tree_node_expanded(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = True

    def on_tree_node_collapsed(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = False

    def _visible_aliases(self) -> list[str]:
        """Sorted aliases the tree shows: all registered, or just the filter."""
        aliases = self._registry.list_aliases()
        if self._filter_alias is not None:
            aliases = [a for a in aliases if a == self._filter_alias]
        aliases.sort()
        return aliases

    @staticmethod
    def _visible_tables(alias: str, schema: object) -> list[Any]:
        """Tables the tree shows for ``alias``. The workspace hides internal/scratch
        schemas (conventionally ``_``-prefixed); every other source shows all tables.

        Shared by ``_build_tree`` and ``_update_status`` so the status-bar count
        always matches what the tree actually renders.
        """
        from tabulaflow.core import SQLSchema

        assert isinstance(schema, SQLSchema)
        tables = list(schema.tables)
        if alias == "workspace":
            tables = [t for t in tables if not (t.schema_name and t.schema_name.startswith("_"))]
        return tables

    def _build_tree(self) -> None:
        from textual.widgets import Tree

        from tabulaflow.core import PropertyGraphSchema, RDFSchema, SQLSchema, SQLTableSchema

        tree = self.query_one("#browse-tree", Tree)

        for alias in self._visible_aliases():
            connector = self._registry.get(alias)
            schema = connector.schema
            if isinstance(schema, PropertyGraphSchema):
                self._add_graph_source_node(
                    tree.root,
                    alias,
                    connector,
                    schema,
                )
                continue
            if isinstance(schema, RDFSchema):
                self._add_rdf_source_node(tree.root, alias, connector, schema)
                continue
            if not isinstance(schema, SQLSchema):
                continue

            source_label = Text()
            source_label.append(alias, style="bold")
            dialect = schema.dialect or getattr(connector, "language", None)
            if dialect:
                source_label.append(f"  {dialect}", style="dim")

            source_node = tree.root.add(
                source_label,
                data=_NodeData(kind=_NODE_KIND_SOURCE, alias=alias),
                expand=self._expand_for((alias, None, None, None), True),
            )

            tables: list[SQLTableSchema] = self._visible_tables(alias, schema)
            schema_names: set[str | None] = {t.schema_name for t in tables}
            has_schemas = schema_names != {None}

            if has_schemas:
                groups: dict[str | None, list[SQLTableSchema]] = {}
                for t in tables:
                    groups.setdefault(t.schema_name, []).append(t)
                for sn in sorted(groups, key=lambda s: (s is None, s or "")):
                    sn_label = Text()
                    sn_label.append(sn or "(default)", style="bold")
                    sn_label.append("  schema", style="dim")
                    schema_node = source_node.add(
                        sn_label,
                        data=_NodeData(kind=_NODE_KIND_SCHEMA, alias=alias, schema_name=sn),
                        expand=self._expand_for((alias, sn, None, None), True),
                    )
                    for t in sorted(groups[sn], key=lambda t: t.name):
                        self._add_table_node(schema_node, alias, t)
            else:
                for t in sorted(tables, key=lambda t: t.name):
                    self._add_table_node(source_node, alias, t)

    def _add_rdf_source_node(
        self,
        parent: object,
        alias: str,
        connector: DataConnector,
        schema: object,
    ) -> None:
        from tabulaflow.core import RDFSchema

        assert isinstance(schema, RDFSchema)
        parent_node: Any = parent

        source_label = Text()
        source_label.append(alias, style="bold")
        source_label.append(f"  {connector.backend}", style="dim")
        parent_node.add_leaf(
            source_label,
            data=_NodeData(
                kind=_NODE_KIND_SOURCE,
                alias=alias,
                path=(alias, None, None, None),
                status_text=f"{alias}  |  RDF source  |  {connector.language}",
            ),
        )

    def _add_graph_source_node(
        self,
        parent: object,
        alias: str,
        connector: DataConnector,
        schema: object,
    ) -> None:
        from tabulaflow.core import PropertyGraphSchema

        assert isinstance(schema, PropertyGraphSchema)
        parent_node: Any = parent
        node_types_label = _GRAPH_GROUP_LABELS[_GRAPH_NODE_TYPES]
        rel_types_label = _GRAPH_GROUP_LABELS[_GRAPH_REL_TYPES]

        source_label = Text()
        source_label.append(alias, style="bold")
        source_label.append(f"  {connector.backend}", style="dim")

        source_node = parent_node.add(
            source_label,
            data=_NodeData(
                kind=_NODE_KIND_SOURCE,
                alias=alias,
                path=(alias, None, None, None),
                status_text=(
                    f"{alias}  |  {len(schema.nodes):,} {node_types_label}  |  "
                    f"{len(schema.relationships):,} {rel_types_label}"
                ),
            ),
            expand=self._expand_for((alias, None, None, None), False),
        )

        nodes = source_node.add(
            Text(node_types_label, style="bold"),
            data=_NodeData(
                kind=_NODE_KIND_GRAPH_GROUP,
                alias=alias,
                path=(alias, _GRAPH_NODE_TYPES, None, None),
                status_text=f"{alias} > {node_types_label}  |  {len(schema.nodes):,} labels",
            ),
            expand=self._expand_for((alias, _GRAPH_NODE_TYPES, None, None), True),
        )
        for node in sorted(schema.nodes, key=lambda n: n.label):
            label_node = nodes.add(
                Text(node.label),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_NODE,
                    alias=alias,
                    path=(alias, _GRAPH_NODE_TYPES, node.label, None),
                    status_text=(
                        f"{alias} > {node_types_label} > {node.label}  |  {len(node.properties):,} properties"
                    ),
                ),
                expand=self._expand_for((alias, _GRAPH_NODE_TYPES, node.label, None), False),
            )
            self._add_graph_properties(
                label_node,
                alias,
                identity_path=(_GRAPH_NODE_TYPES, node.label),
                display_path=(node_types_label, node.label),
                properties=node.properties,
            )

        relationships = source_node.add(
            Text(rel_types_label, style="bold"),
            data=_NodeData(
                kind=_NODE_KIND_GRAPH_GROUP,
                alias=alias,
                path=(alias, _GRAPH_REL_TYPES, None, None),
                status_text=f"{alias} > {rel_types_label}  |  {len(schema.relationships):,} types",
            ),
            expand=self._expand_for((alias, _GRAPH_REL_TYPES, None, None), True),
        )
        for rel in sorted(schema.relationships, key=lambda rel: rel.label):
            rel_path = (_GRAPH_REL_TYPES, rel.label, None, None)
            rel_node = relationships.add(
                Text(rel.label),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_RELATIONSHIP,
                    alias=alias,
                    path=(alias, *rel_path),
                    status_text=(f"{alias} > {rel_types_label} > {rel.label}  |  {len(rel.properties):,} properties"),
                ),
                expand=self._expand_for((alias, *rel_path), False),
            )
            self._add_graph_properties(
                rel_node,
                alias,
                identity_path=rel_path,
                display_path=(rel_types_label, rel.label),
                properties=rel.properties,
            )

    def _add_graph_properties(
        self,
        parent: object,
        alias: str,
        *,
        identity_path: tuple[str | None, ...],
        display_path: tuple[str, ...],
        properties: list[Any],
    ) -> None:
        from tabulaflow.core import GraphPropertySchema

        parent_node: Any = parent
        name_width = max((len(prop.name) for prop in properties if isinstance(prop, GraphPropertySchema)), default=0)
        for prop in properties:
            assert isinstance(prop, GraphPropertySchema)
            parent_label = " > ".join(display_path)
            types = " | ".join(prop.types)
            parent_node.add_leaf(
                Text.assemble(prop.name.ljust(name_width), (f"  {types}", "dim")),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_PROPERTY,
                    alias=alias,
                    path=(alias, *identity_path, prop.name),
                    status_text=f"{alias} > {parent_label} > {prop.name}  |  {types}",
                ),
            )

    def _add_table_node(self, parent: object, alias: str, table: object) -> None:
        from tabulaflow.core import SQLTableSchema

        assert isinstance(table, SQLTableSchema)
        parent_node: Any = parent

        t_label = Text()
        t_label.append(table.name)
        if table.is_view:
            t_label.append("  view", style="dim")

        table_node = parent_node.add(
            t_label,
            data=_NodeData(
                kind=_NODE_KIND_TABLE,
                alias=alias,
                schema_name=table.schema_name,
                table_name=table.name,
            ),
            expand=self._expand_for((alias, table.schema_name, table.name, None), False),
        )

        name_width = max((len(col.name) for col in table.columns), default=0)
        primary_key_columns = set(table.primary_key)
        foreign_key_columns = {name for foreign_key in table.foreign_keys for name in foreign_key.columns}
        for col in table.columns:
            c_label = Text()
            c_label.append(col.name.ljust(name_width))
            c_label.append(f"  {col.dtype}", style="dim")
            if col.name in primary_key_columns:
                c_label.append(" PK", style=PK_MARKER)
            if col.name in foreign_key_columns:
                c_label.append(" FK", style=FK_MARKER)
            table_node.add_leaf(
                c_label,
                data=_NodeData(
                    kind=_NODE_KIND_COLUMN,
                    alias=alias,
                    schema_name=table.schema_name,
                    table_name=table.name,
                    column_name=col.name,
                ),
            )

    async def action_open_preview(self) -> None:
        """Open DataBrowserScreen for the table under the cursor.

        For writable SQL connectors (``read_only=False``), runs a live
        ``SELECT * ... LIMIT 10`` so the preview reflects the current
        source state. For read-only or non-SQL connectors, falls back
        to the cached ``sampled_df``.
        """
        from textual.widgets import Tree

        from tabulaflow.core import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return

        connector = self._registry.get(node_data.alias)
        from tabulaflow.data.sql import SQLConnector

        assert isinstance(connector, SQLConnector)
        schema = connector.schema
        assert isinstance(schema, SQLSchema)
        # SQLSchema implies a SQL connector; the live preview path uses
        # SQLAlchemy ``Executable`` which only ``SQLConnector``
        # accepts.
        assert node_data.table_name is not None
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        if table is None:
            return

        import pandas as pd
        import sqlalchemy

        tbl = sqlalchemy.table(
            node_data.table_name,
            schema=node_data.schema_name,
        )
        stmt = sqlalchemy.select("*").select_from(tbl).limit(self._PREVIEW_ROW_CAP)
        self._status.update(Text("Loading preview...", style="dim"))
        result = await connector.run_query_async(stmt, timeout=30)
        if result.error is not None:
            msg = result.error.message.replace("\n", " ").strip()
            self._status.update(Text.from_markup(f"[{ERROR}]Preview error:[/] {msg}"))
            return
        self._update_status()
        df = result.df if result.df is not None else pd.DataFrame()

        suffix = f"(first {self._PREVIEW_ROW_CAP} rows)"
        title = (
            f"{node_data.alias}: {node_data.schema_name}.{node_data.table_name} {suffix}"
            if node_data.schema_name
            else f"{node_data.alias}: {node_data.table_name} {suffix}"
        )
        self.app.push_screen(DataBrowserScreen(title=title, df=df))

    def action_close_browser(self) -> None:
        self.dismiss()

    async def action_refresh_schema(self) -> None:
        """Re-introspect the visible data sources and rebuild the tree in place.

        Re-reads each shown connector's schema directly from the live
        source, so DDL run outside the agent (or by it) shows up here on
        demand. Cursor and expansion state are preserved across the
        rebuild. Re-introspection can be slow on cloud warehouses, so the
        key is a no-op while a refresh is already in flight.
        """
        from textual.widgets import Tree

        if self._refreshing:
            return
        self._refreshing = True
        # Snapshot before clearing: ``tree.clear()`` moves the cursor and
        # fires ``on_tree_node_highlighted``, which would overwrite
        # ``_state.cursor`` (same hazard guarded against in ``on_mount``).
        saved_cursor = self._state.cursor
        self._status.update(Text("Refreshing schema...", style="dim"))
        try:
            failures: list[str] = []
            for alias in self._visible_aliases():
                connector = self._registry.get(alias)
                try:
                    await connector.refresh_schema_async()
                except Exception as e:  # noqa: BLE001 - surface, don't crash the screen
                    failures.append(f"{alias} ({type(e).__name__})")

            tree = self.query_one("#browse-tree", Tree)
            tree.clear()
            self._build_tree()
            self._update_status()
            self._update_hint()
            self.call_after_refresh(self._restore_cursor, saved_cursor)

            # On success the rebuilt tree is the feedback; only surface
            # failures. Deferred so it lands after ``_restore_cursor``'s
            # highlight re-runs ``_update_status`` (which would clobber it).
            if failures:
                msg = "Schema refresh failed: " + ", ".join(failures)
                self.call_after_refresh(
                    self._status.update,
                    Text.from_markup(f"[{ERROR}]{msg}[/]"),
                )
        finally:
            self._refreshing = False

    def action_collapse_node(self) -> None:
        """Collapse the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.collapse()

    def action_expand_node(self) -> None:
        """Expand the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.expand()

    def on_tree_node_highlighted(self, event: "Any") -> None:
        """Update hint/status bars and record cursor position in state."""
        self._state.cursor = self._node_path(event.node.data)
        self._update_status()
        self._update_hint()

    def _cursor_has_preview(self) -> bool:
        """Return True if the cursor is on a table node with sampled_df."""
        from textual.widgets import Tree

        from tabulaflow.core import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return False
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return False
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            return False
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        return table is not None and table.sampled_df is not None and not table.sampled_df.empty

    def _update_status(self) -> None:
        """Update the status bar with table/column/row counts for the highlighted scope."""
        from textual.widgets import Tree

        from tabulaflow.core import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            self._status.update(Text(""))
            return

        node_data: _NodeData | None = node.data
        if node_data is None:
            self._status.update(Text(""))
            return
        if node_data.status_text is not None:
            self._status.update(Text(node_data.status_text, style="dim"))
            return

        parts: list[str] = []
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            self._status.update(Text(""))
            return

        if node_data.kind == _NODE_KIND_SOURCE:
            tables = self._visible_tables(node_data.alias, schema)
            parts.append(node_data.alias)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind == _NODE_KIND_SCHEMA:
            tables = [
                t for t in self._visible_tables(node_data.alias, schema) if t.schema_name == node_data.schema_name
            ]
            path = f"{node_data.alias} > {node_data.schema_name or '(default)'}"
            parts.append(path)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind in (_NODE_KIND_TABLE, _NODE_KIND_COLUMN):
            table = next(
                (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
                None,
            )
            if table:
                if node_data.schema_name:
                    path = f"{node_data.alias} > {node_data.schema_name}.{node_data.table_name}"
                else:
                    path = f"{node_data.alias} > {node_data.table_name}"
                parts.append(path)
                parts.append(f"{len(table.columns):,} columns")
                if table.num_rows is not None:
                    parts.append(f"{table.num_rows:,} rows")

        if parts:
            self._status.update(Text("  |  ".join(parts), style="dim"))
        else:
            self._status.update(Text(""))

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back", style=hint_fg)
        if self._cursor_has_preview():
            hint.append("    ", style=hint_fg)
            hint.append("↵", style=KEY_HINT)
            hint.append(" Preview table", style=hint_fg)
        hint.append("    ", style=hint_fg)
        hint.append("R", style=KEY_HINT)
        hint.append(" Refresh", style=hint_fg)
        self._hint.update(hint)


_CURRENT_CUSTOM_PRESET_LABEL = "Current custom"
_LLM_OPTION_LABEL_WIDTH = 20
