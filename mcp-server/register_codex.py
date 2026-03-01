"""Register CogniLayer MCP server in Codex CLI config.toml."""

import sys
import tomllib
from pathlib import Path

CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
COGNILAYER_HOME = Path.home() / ".cognilayer"


def _serialize_toml_value(value) -> str:
    """Serialize a Python value to TOML format."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        items = ", ".join(_serialize_toml_value(v) for v in value)
        return f"[{items}]"
    return f'"{value}"'


def _write_toml(data: dict, path: Path):
    """Write a dict to TOML file, preserving existing sections."""
    lines = []
    top_keys = {k: v for k, v in data.items() if not isinstance(v, dict)}
    nested_keys = {k: v for k, v in data.items() if isinstance(v, dict)}

    # Top-level keys
    for k, v in top_keys.items():
        lines.append(f"{k} = {_serialize_toml_value(v)}")

    if top_keys and nested_keys:
        lines.append("")

    # Nested sections
    for section, values in nested_keys.items():
        # Check for sub-tables (e.g. mcp_servers.cognilayer)
        has_sub = any(isinstance(v, dict) for v in values.values())
        if has_sub:
            for sub_name, sub_values in values.items():
                if isinstance(sub_values, dict):
                    lines.append(f"[{section}.{sub_name}]")
                    for k, v in sub_values.items():
                        lines.append(f"{k} = {_serialize_toml_value(v)}")
                    lines.append("")
                else:
                    # Top-level key in section namespace — write under [section]
                    pass
        else:
            lines.append(f"[{section}]")
            for k, v in values.items():
                lines.append(f"{k} = {_serialize_toml_value(v)}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def register():
    """Add CogniLayer MCP server to ~/.codex/config.toml."""
    home_str = str(COGNILAYER_HOME).replace("\\", "/")
    server_path = f"{home_str}/mcp-server/server.py"
    python_cmd = sys.executable.replace("\\", "/")

    # Read existing config
    data = {}
    if CODEX_CONFIG.exists():
        with open(CODEX_CONFIG, "rb") as f:
            data = tomllib.load(f)

    # Ensure mcp_servers section exists
    if "mcp_servers" not in data:
        data["mcp_servers"] = {}

    # Set CogniLayer server entry (idempotent — overwrites existing)
    data["mcp_servers"]["cognilayer"] = {
        "command": python_cmd,
        "args": [server_path],
        "startup_timeout_sec": 15,
        "enabled": True,
    }

    # Write config
    CODEX_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _write_toml(data, CODEX_CONFIG)

    print(f"CogniLayer registered in {CODEX_CONFIG}")
    print(f"  MCP server: {server_path}")
    print(f"  Command: {python_cmd}")
    print(f"  Note: Codex has no hooks. Use AGENTS.md instructions instead.")
    return data


if __name__ == "__main__":
    register()
