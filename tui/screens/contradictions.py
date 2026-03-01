"""Tab 7: Contradictions — Contradiction review."""

from textual.app import ComposeResult
from textual.widgets import DataTable, Static, Button
from textual.containers import Vertical

from tui import data


class ContradictionsScreen(Static):
    """Contradictions browser with resolve action."""

    DEFAULT_CSS = """
    ContradictionsScreen {
        height: 1fr;
    }
    """

    def __init__(self, project: str | None = None, **kwargs):
        self.project = project
        self._contradictions = []
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield DataTable(id="contradictions-table")

    def on_mount(self) -> None:
        table = self.query_one("#contradictions-table", DataTable)
        table.add_columns("Fact A", "Fact B", "Reason", "Detected", "Status")
        table.cursor_type = "row"

        self._load_data()

    def _load_data(self):
        table = self.query_one("#contradictions-table", DataTable)
        table.clear()

        self._contradictions = data.get_contradictions(self.project)

        for c in self._contradictions:
            fact_a = (c.get("fact_a_content") or "?")[:35]
            fact_b = (c.get("fact_b_content") or "?")[:35]
            reason = (c.get("reason") or "-")[:30]
            detected = (c.get("detected") or "?")[:10]
            resolved = c.get("resolved", 0)

            if resolved:
                status = "[green]Resolved[/]"
            else:
                status = "[red]Open[/]"

            table.add_row(fact_a, fact_b, reason, detected, status, key=str(c.get("id", "")))

    def on_key(self, event) -> None:
        if event.key == "r":
            table = self.query_one("#contradictions-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self._contradictions):
                c = self._contradictions[table.cursor_row]
                if not c.get("resolved"):
                    data.resolve_contradiction(c["id"])
                    self._load_data()
                    self.notify("Contradiction resolved", severity="information")
