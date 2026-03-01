"""Tab 1: Overview — Stats dashboard."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from tui.widgets.stats_card import StatsCard
from tui import data


class OverviewScreen(Static):
    """Overview dashboard with stats grid and health metrics."""

    DEFAULT_CSS = """
    OverviewScreen {
        height: auto;
        padding: 1;
    }
    .stats-row {
        height: 7;
        margin-bottom: 1;
    }
    .health-section {
        height: auto;
        padding: 1;
        border: solid $surface;
        margin-bottom: 1;
    }
    .session-section {
        height: auto;
        padding: 1;
        border: solid $surface;
    }
    """

    def __init__(self, project: str | None = None, **kwargs):
        self.project = project
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        stats = data.get_stats(self.project)

        with Horizontal(classes="stats-row"):
            yield StatsCard("Facts", stats["facts"], color="white")
            yield StatsCard("Sessions", stats["sessions"], color="green")
            yield StatsCard("Changes", stats["changes"], color="blue")
            yield StatsCard("Projects", stats["projects"], color="magenta")

        with Horizontal(classes="stats-row"):
            yield StatsCard("Hot", stats["hot"], color="red")
            yield StatsCard("Warm", stats["warm"], color="yellow")
            yield StatsCard("Cold", stats["cold"], color="cyan")
            yield StatsCard("Gaps", stats["gaps"], color="dark_orange")

        with Vertical(classes="health-section"):
            total = stats["facts"] or 1
            hot_pct = stats["hot"] / total * 100
            warm_pct = stats["warm"] / total * 100
            cold_pct = stats["cold"] / total * 100
            yield Static(
                f"[bold]Memory Health[/]\n"
                f"  [red]Hot:  {stats['hot']:>4} ({hot_pct:5.1f}%)[/]  "
                f"[yellow]Warm: {stats['warm']:>4} ({warm_pct:5.1f}%)[/]  "
                f"[cyan]Cold: {stats['cold']:>4} ({cold_pct:5.1f}%)[/]\n"
                f"  Contradictions: {stats['contradictions']}  |  Knowledge Gaps: {stats['gaps']}"
            )

        last = stats.get("last_session")
        if last:
            with Vertical(classes="session-section"):
                title = last.get("episode_title") or "Untitled"
                outcome = last.get("outcome") or "?"
                bridge = last.get("bridge_content") or "No bridge"
                # Truncate bridge
                if len(bridge) > 200:
                    bridge = bridge[:200] + "..."
                yield Static(
                    f"[bold]Last Session[/]\n"
                    f"  [{_outcome_color(outcome)}]{outcome}[/] — {title}\n"
                    f"  {last.get('start_time', '?')}\n"
                    f"  [dim]{bridge}[/]"
                )


def _outcome_color(outcome: str) -> str:
    o = (outcome or "").lower()
    if o in ("success", "completed"):
        return "green"
    if o in ("partial", "interrupted"):
        return "yellow"
    if o in ("failed", "crashed"):
        return "red"
    return "white"
