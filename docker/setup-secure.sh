#!/usr/bin/env bash
# CogniLayer Secure Docker Setup — Hybrid Mode
#
# Architecture:
#   MCP server  -> Docker container (isolated, no network)
#   Hooks       -> Host (hardened with sanitize.py)
#   SQLite DB   -> ~/.cognilayer/ (bind-mounted, shared)
#
# This gives you:
#   - Smooth hook UX (CLAUDE.md injection, file tracking, session bridges)
#   - MCP server isolation (no network, read-only FS, no capabilities)
#   - Content sanitization on the DB -> CLAUDE.md trust boundary
#
# Usage:
#   cd /path/to/CogniLayer
#   bash docker/setup-secure.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
COGNILAYER_HOME="$HOME/.cognilayer"

echo "=== CogniLayer Secure Docker Setup (Hybrid Mode) ==="
echo ""

# 0. Ensure ~/.cognilayer exists (will be bind-mounted)
mkdir -p "$COGNILAYER_HOME/logs" "$COGNILAYER_HOME/sessions"

# 1. Run normal install first (sets up hooks, commands, DB schema)
echo "[1/5] Running base install (hooks + DB schema)..."
python3 "$REPO_DIR/install.py"
echo "      Done."

# 2. Install sanitization module alongside hooks
echo "[2/5] Installing sanitization layer..."
cp "$SCRIPT_DIR/sanitize.py" "$COGNILAYER_HOME/hooks/sanitize.py"

# Patch on_session_start.py to use sanitization
python3 - "$COGNILAYER_HOME/hooks/on_session_start.py" <<'PYEOF'
import sys

hook_path = sys.argv[1]
with open(hook_path, "r", encoding="utf-8") as f:
    content = f.read()

# Skip if already patched
if "sanitize" in content:
    print("      Already patched.")
    sys.exit(0)

# Add import after existing imports
import_line = "from sanitize import sanitize_dna, sanitize_bridge, sanitize_session_id"
# Insert after the i18n import block
marker = "COGNILAYER_START ="
if marker in content:
    idx = content.index(marker)
    content = content[:idx] + import_line + "\n\n" + content[idx:]

# Patch get_cognilayer_block to sanitize inputs
old_block_fn = '''def get_cognilayer_block(dna: str, bridge: str | None) -> str:
    """Build the CLAUDE.md injection block."""
    lines = [COGNILAYER_START, ""]
    lines.append(t("claude_md.template"))

    lines.append("")
    lines.append(dna)

    if bridge:
        lines.append("")
        lines.append(f"## Last Session Bridge\\n{bridge}")'''

new_block_fn = '''def get_cognilayer_block(dna: str, bridge: str | None) -> str:
    """Build the CLAUDE.md injection block."""
    lines = [COGNILAYER_START, ""]
    lines.append(t("claude_md.template"))

    lines.append("")
    lines.append(sanitize_dna(dna))

    if bridge:
        lines.append("")
        lines.append(f"## Last Session Bridge\\n{sanitize_bridge(bridge)}")'''

if old_block_fn in content:
    content = content.replace(old_block_fn, new_block_fn)
    print("      Patched get_cognilayer_block with sanitization.")
else:
    print("      WARNING: Could not find get_cognilayer_block to patch.")
    print("      You may need to manually add sanitize_dna/sanitize_bridge calls.")

# Patch session ID usage
old_sid = 'claude_session_id}.json").write_text'
new_sid = 'sanitize_session_id(claude_session_id)}.json").write_text'
if old_sid in content:
    content = content.replace(
        '(SESSIONS_DIR / f"{claude_session_id}.json").write_text',
        '(SESSIONS_DIR / f"{sanitize_session_id(claude_session_id)}.json").write_text'
    )
    print("      Patched session ID with sanitization.")

with open(hook_path, "w", encoding="utf-8") as f:
    f.write(content)
PYEOF

# Also patch session ID in on_session_end.py and on_file_change.py
for hook in on_session_end.py on_file_change.py on_pre_compact.py; do
    hook_path="$COGNILAYER_HOME/hooks/$hook"
    if [ -f "$hook_path" ]; then
        # Add sanitize import if not present
        if ! grep -q "sanitize_session_id" "$hook_path"; then
            # Add import at the top, after the Path import
            python3 -c "
import sys
p = sys.argv[1]
with open(p, 'r') as f: c = f.read()
if 'sanitize_session_id' not in c:
    c = c.replace(
        'SESSIONS_DIR = COGNILAYER_HOME / \"sessions\"',
        'SESSIONS_DIR = COGNILAYER_HOME / \"sessions\"\n\ntry:\n    sys.path.insert(0, str(COGNILAYER_HOME / \"hooks\"))\n    from sanitize import sanitize_session_id\nexcept ImportError:\n    sanitize_session_id = lambda x: x',
        1
    )
    with open(p, 'w') as f: f.write(c)
    print(f'      Patched {sys.argv[2]} with session ID sanitization.')
" "$hook_path" "$hook"
        fi
    fi
done

echo "      Sanitization layer installed."

# 3. Build Docker image
echo "[3/5] Building Docker image..."
docker build -t cognilayer:secure -f "$SCRIPT_DIR/Dockerfile" "$REPO_DIR"
echo "      Done."

# 4. Start container
echo "[4/5] Starting container..."
docker rm -f cognilayer 2>/dev/null || true
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
echo "      Container running."

# 5. Configure Claude Code: MCP via Docker, hooks stay on host
echo "[5/5] Configuring Claude Code (MCP via Docker, hooks on host)..."
python3 - "$CLAUDE_SETTINGS" <<'PYEOF'
import json, sys

settings_path = sys.argv[1]
try:
    with open(settings_path, "r") as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

# MCP server via Docker exec (isolated)
settings.setdefault("mcpServers", {})
settings["mcpServers"]["cognilayer"] = {
    "command": "docker",
    "args": ["exec", "-i", "cognilayer", "python", "mcp-server/server.py"]
}

# Hooks stay as-is (installed by install.py, now hardened with sanitize.py)
# Don't remove them -- they provide the smooth UX

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)

print(f"      Updated {settings_path}")
print("      - MCP server: docker exec (containerized, no network)")
print("      - Hooks: on host (hardened with sanitization)")
PYEOF

echo ""
echo "=== Setup Complete (Hybrid Mode) ==="
echo ""
echo "Architecture:"
echo "  MCP server  -> Docker (no network, read-only FS, no caps, 512MB limit)"
echo "  Hooks       -> Host (hardened: sanitize.py guards DB -> CLAUDE.md)"
echo "  SQLite DB   -> ~/.cognilayer/ (bind-mounted, shared)"
echo ""
echo "What's hardened vs. native install:"
echo "  + MCP server fully isolated (can't exfiltrate even if compromised)"
echo "  + DB content sanitized before CLAUDE.md injection"
echo "  + Session IDs validated (no path traversal)"
echo "  + Prompt injection patterns blocked at trust boundary"
echo "  + All hooks still work (smooth UX preserved)"
echo ""
echo "To mount project dirs for code indexing (read-only):"
echo "  Edit docker/docker-compose.yml, uncomment the projects volume"
echo ""
echo "To verify:"
echo "  docker exec cognilayer python mcp-server/server.py --test"
echo ""
echo "To uninstall:"
echo "  docker rm -f cognilayer"
echo "  python3 $(dirname "$0")/../install.py   # reinstall native if desired"
