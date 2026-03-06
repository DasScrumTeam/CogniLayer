# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CogniLayer is a persistent knowledge layer and code intelligence MCP server for AI coding agents (Claude Code, Codex CLI). It provides 17 MCP tools for memory management, code graph analysis, session continuity, and deployment safety. Written in Python 3.11+, backed by SQLite (WAL mode, FTS5, optional sqlite-vec for vector search).

## Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_memory_search.py -v

# Run a single test
python -m pytest tests/test_memory_search.py::test_function_name -v

# Install dependencies (what CI uses)
pip install pytest mcp pyyaml tree-sitter-language-pack

# Verify MCP server works (registers all 17 tools)
python ~/.cognilayer/mcp-server/server.py --test

# Run diagnostics
python diagnose.py
python diagnose.py --fix

# Install to ~/.cognilayer/
python install.py              # Claude Code
python install.py --codex      # Codex CLI
python install.py --both       # Both
```

## Architecture

### Runtime Layout

The repo is a **source tree** that gets installed to `~/.cognilayer/` via `install.py`. The installed copy is what Claude Code/Codex CLI actually uses. During development, work in this repo and re-run `install.py` to deploy changes.

### Three Subsystems

1. **MCP Server** (`mcp-server/`) - 17 tool implementations registered via the `mcp` library's `Server` class. Entry point: `server.py`. Each tool is a standalone module in `mcp-server/tools/` that imports shared DB helpers from `db.py` and session state from `utils.py`.

2. **Hooks** (`hooks/`) - Claude Code lifecycle hooks (SessionStart, SessionEnd, PreCompact, PostToolUse). These are Python scripts invoked by Claude Code at specific points. They write to the same SQLite DB. `hooks/register.py` handles registration in `~/.claude/settings.json`.

3. **TUI** (`tui/`) - Read-only Textual dashboard with 8 tab screens. Entry point: `tui/__main__.py` (also accessible via `bin/cognilayer` CLI wrapper). Data access is through `tui/data.py`.

### Key Design Patterns

- **All state in one SQLite DB** (`~/.cognilayer/memory.db`) - 17+ tables, WAL mode for concurrent access, 30s busy_timeout for multi-CLI safety.
- **Two DB openers**: `open_db()` (full, with logging and optional vec) for MCP server tools; `open_db_fast()` (minimal, no logging) for hooks that need <1ms overhead.
- **Tool modules are self-contained**: each file in `mcp-server/tools/` exports a single async function matching the tool name. Tools get the active project/session via `utils.get_active_session()`.
- **i18n via `i18n.py`**: all user-facing strings use `t("key")`, supporting EN and CS locales.
- **Code intelligence** (`mcp-server/code/`): tree-sitter AST parsing with a parser registry (`parsers/registry.py`). Language-specific parsers inherit from `parsers/base.py`. The `resolver.py` handles cross-file symbol reference resolution.
- **Search** (`mcp-server/search/`): hybrid FTS5 + vector search. Vector search is optional (requires `fastembed` + `sqlite-vec`). FTS5 works standalone.

### Test Fixtures

Tests use `conftest.py` fixtures `temp_db` and `active_session` which monkeypatch `db.DB_PATH` and `utils.get_active_session` to isolate tests with temporary SQLite databases. No external services needed.

### CI

GitHub Actions runs `python -m pytest tests/ -v` on Python 3.11 and 3.12 across Ubuntu and Windows.
