"""Stats card widget for overview dashboard."""

from textual.widgets import Static


class StatsCard(Static):
    """A statistics card showing a label and value."""

    DEFAULT_CSS = """
    StatsCard {
        width: 1fr;
        height: 5;
        border: solid $accent;
        padding: 1 2;
        text-align: center;
    }
    """

    def __init__(self, label: str, value: str | int, color: str = "white", **kwargs):
        self.label = label
        self.value = str(value)
        self.color = color
        super().__init__(**kwargs)

    def render(self) -> str:
        return f"[bold {self.color}]{self.value}[/]\n[dim]{self.label}[/]"

    def update_value(self, value: str | int):
        self.value = str(value)
        self.refresh()
