Launch the CogniLayer TUI Dashboard for visual memory management.

Run this command:
```
python ~/.cognilayer/tui/app.py
```

If you want a specific project, add `--project <name>`:
```
python ~/.cognilayer/tui/app.py --project $ARGUMENTS
```

The TUI has 7 tabs:
1. **Overview** — Stats, health metrics, last session
2. **Facts** — Browseable fact list with search/filters
3. **Heatmap** — Heat score distribution by type and project
4. **Clusters** — Fact clusters tree view
5. **Timeline** — Session history with episodes
6. **Gaps** — Knowledge gaps tracker
7. **Contradictions** — Contradiction review (press R to resolve)

Keyboard: 1-7 for tabs, Q to quit, R to refresh.
