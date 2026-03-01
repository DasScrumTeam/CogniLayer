"""Entry point: python -m cognilayer.tui or python ~/.cognilayer/tui/__main__.py."""

import sys
from pathlib import Path

# Ensure tui package and mcp-server are importable
tui_dir = Path(__file__).parent
sys.path.insert(0, str(tui_dir.parent))
sys.path.insert(0, str(tui_dir.parent / "mcp-server"))

from tui.app import CogniLayerTUI


def main():
    project = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--project" and i < len(sys.argv) - 1:
            project = sys.argv[i + 1]

    app = CogniLayerTUI(project=project)
    app.run()


if __name__ == "__main__":
    main()
