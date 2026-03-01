"""Tab 2: Facts — Filterable fact browser."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, Select, Static
from textual.message import Message

from tui.widgets.heat_cell import heat_color, heat_label
from tui import data


class FactsScreen(Static):
    """Fact browser with search and filters."""

    DEFAULT_CSS = """
    FactsScreen {
        height: 1fr;
    }
    .filter-bar {
        height: 3;
        padding: 0 1;
        dock: top;
    }
    .filter-bar Input {
        width: 1fr;
    }
    .filter-bar Select {
        width: 20;
    }
    """

    def __init__(self, project: str | None = None, **kwargs):
        self.project = project
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        types = [("All types", None)] + [(t, t) for t in data.get_fact_types(self.project)]
        domains = [("All domains", None)] + [(d, d) for d in data.get_fact_domains(self.project)]
        tiers = [("All tiers", None), ("active", "active"), ("reference", "reference"), ("archive", "archive")]

        with Horizontal(classes="filter-bar"):
            yield Input(placeholder="Search facts...", id="fact-search")
            yield Select(types, id="type-filter", value=None)
            yield Select(domains, id="domain-filter", value=None)
            yield Select(tiers, id="tier-filter", value=None)

        yield DataTable(id="facts-table")

    def on_mount(self) -> None:
        table = self.query_one("#facts-table", DataTable)
        table.add_columns("Type", "Domain", "Content", "Heat", "Tier", "Age")
        self._load_data()

    def _load_data(self):
        table = self.query_one("#facts-table", DataTable)
        table.clear()

        search_input = self.query_one("#fact-search", Input)
        type_select = self.query_one("#type-filter", Select)
        domain_select = self.query_one("#domain-filter", Select)
        tier_select = self.query_one("#tier-filter", Select)

        type_val = type_select.value if type_select.value != Select.BLANK else None
        domain_val = domain_select.value if domain_select.value != Select.BLANK else None
        tier_val = tier_select.value if tier_select.value != Select.BLANK else None

        facts = data.get_facts(
            project=self.project,
            type_filter=type_val,
            domain_filter=domain_val,
            tier_filter=tier_val,
            search=search_input.value or None,
        )

        for fact in facts:
            heat = fact.get("heat_score", 0) or 0
            color = heat_color(heat)
            content = (fact.get("content") or "")[:60]
            age = _format_age(fact.get("timestamp"))

            table.add_row(
                fact.get("type", "?"),
                fact.get("domain") or "-",
                content,
                f"[{color}]{heat_label(heat)} {heat:.2f}[/]",
                fact.get("knowledge_tier") or "?",
                age,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "fact-search":
            self._load_data()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._load_data()


def _format_age(timestamp: str | None) -> str:
    if not timestamp:
        return "?"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp)
        delta = datetime.now() - dt
        if delta.days > 30:
            return f"{delta.days // 30}mo"
        if delta.days > 0:
            return f"{delta.days}d"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h"
        return f"{delta.seconds // 60}m"
    except Exception:
        return "?"
