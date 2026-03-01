# CogniLayer

**Persistent memory for Claude Code & Codex CLI.** CogniLayer gives AI coding agents a long-term memory that survives across sessions, projects, and crashes.

**Save ~80-100K tokens per session** — instead of re-reading files and re-discovering architecture from scratch, CogniLayer injects compact context in a few kilobytes.

Built as an [MCP server](https://modelcontextprotocol.io/) + hooks system that integrates directly into Claude Code and Codex CLI workflows.

## The Problem

Every time you start a new Claude Code session, it forgets everything. Your project's architecture, past decisions, deployment details, debugging insights — all gone. You waste tokens re-explaining the same context over and over.

## The Solution

CogniLayer automatically:
- **Remembers** facts, decisions, patterns, and gotchas across sessions
- **Detects staleness** — warns you when a remembered fact references a changed file
- **Bridges sessions** — summarizes what happened last time so the next session can pick up where you left off
- **Indexes your docs** — chunks PRDs, READMEs, and configs into searchable pieces
- **Guards deployments** — Identity Card system prevents deploying to the wrong server
- **Works across projects** — search knowledge from one project while working on another
- **Links knowledge** — Zettelkasten-style fact linking, causal chains, cluster organization
- **TUI Dashboard** — Visual memory browser with 7 tabs

## How It Works

```
Claude Code / Codex CLI Session
    │
    ├── SessionStart hook (Claude Code) / session_init tool (Codex)
    │   └── Injects Project DNA + last session bridge
    │
    ├── MCP Server (13 tools)
    │   ├── memory_search   — Find facts with staleness detection
    │   ├── memory_write    — Store facts (14 types, deduplication)
    │   ├── memory_delete   — Remove outdated facts
    │   ├── memory_link     — Manually link related facts
    │   ├── memory_chain    — Create causal chains (cause → effect)
    │   ├── file_search     — Search indexed project docs
    │   ├── project_context — Get project DNA + health metrics
    │   ├── session_bridge  — Save/load session continuity
    │   ├── session_init    — Initialize session (Codex CLI)
    │   ├── decision_log    — Query past decisions
    │   ├── verify_identity — Safety gate before deploy/SSH/push
    │   ├── identity_set    — Configure project Identity Card
    │   └── recommend_tech  — Suggest tech stacks from similar projects
    │
    ├── PostToolUse hook (Claude Code only)
    │   └── Logs every file Write/Edit (<1ms overhead)
    │
    └── SessionEnd hook / session_bridge(save)
        └── Closes session, builds emergency bridge if needed
```

## Features

### 14 Fact Types
Not just dumb notes — structured knowledge:
`decision` `fact` `pattern` `issue` `task` `skill` `gotcha` `procedure` `error_fix` `command` `performance` `api_contract` `dependency` `client_rule`

### Staleness Detection
When you search memory, CogniLayer checks if the source file has changed since the fact was recorded. Changed facts are marked with `STALE` so you know to verify before acting.

### Session Bridges
Every session gets a summary — what was done, what's open, key decisions. The next session automatically gets this context injected.

### Knowledge Organization (V3)
- **Fact linking** — Bidirectional Zettelkasten-style connections between facts
- **Causal chains** — Track cause→effect relationships (caused, led_to, blocked, fixed, broke)
- **Memory consolidation** — Clusters related facts, assigns knowledge tiers (active/reference/archive)
- **Contradiction detection** — Finds conflicting facts during consolidation
- **Knowledge gaps** — Tracks weak/failed searches to identify missing knowledge
- **Retrieval tracking** — Counts how often facts are accessed, surfaces unused knowledge

### Project Identity Card
Stores deployment configuration (SSH, ports, domains, PM2 processes) with:
- **Safety locking** — locked fields can't be changed without explicit update + audit log
- **Hash verification** — detects tampering of safety fields
- **Required field checks** — blocks deploy if critical fields are missing

### Crash Recovery
If a session crashes (kill, timeout, error), the next session detects the orphan and builds an emergency bridge from the change log.

### Hybrid Search
- **FTS5** fulltext search for keyword matching
- **Vector embeddings** via [fastembed](https://github.com/qdrant/fastembed) (CPU-only, ONNX, no GPU needed)
- **sqlite-vec** for vector storage directly in SQLite
- Hybrid ranker combines both scores (40% FTS5 + 60% vector similarity)

### Heat Decay
Facts have a "temperature" that changes over time:
- **Hot** (0.7-1.0) — recently accessed, high relevance
- **Warm** (0.3-0.7) — moderately recent
- **Cold** (0.05-0.3) — old, rarely accessed

### TUI Dashboard
Visual memory browser with 7 tabs:
1. **Overview** — Stats, health metrics, last session
2. **Facts** — Searchable fact list with type/domain/tier filters
3. **Heatmap** — Heat score distribution by type and project
4. **Clusters** — Fact cluster tree view
5. **Timeline** — Session history with episodes and outcomes
6. **Gaps** — Knowledge gap tracker
7. **Contradictions** — Review and resolve contradictions

```bash
python ~/.cognilayer/tui/app.py                    # All projects
python ~/.cognilayer/tui/app.py --project my-app   # Specific project
```

### Codex CLI Support
CogniLayer works with OpenAI's Codex CLI in addition to Claude Code:
- Registers as MCP server in `~/.codex/config.toml`
- `session_init` tool replaces hooks (Codex has no hook system)
- `AGENTS.md` generator provides Codex-specific instructions
- Same memory DB shared between both CLIs

## Installation

### Requirements
- Python 3.11+ (for `tomllib`)
- Claude Code and/or Codex CLI
- pip packages: `mcp`, `pyyaml` (required), `fastembed`, `sqlite-vec` (optional), `textual` (optional, for TUI)

### Quick Install

```bash
# Clone the repo
git clone https://github.com/LakyFx/CogniLayer.git
cd CogniLayer

# Install for Claude Code (default)
python install.py

# Install for Codex CLI
python install.py --codex

# Install for both
python install.py --both
```

The installer will:
1. Check Python version and dependencies
2. Copy files to `~/.cognilayer/`
3. Copy slash commands to `~/.claude/commands/`
4. **Backup** existing database before migration
5. Initialize/upgrade the SQLite database (non-destructive)
6. Register MCP server and hooks

### Optional Dependencies

```bash
# For hybrid vector search (recommended)
pip install fastembed sqlite-vec

# For TUI dashboard
pip install textual
```

### Verify Installation

```bash
# Test MCP server
python ~/.cognilayer/mcp-server/server.py --test
# Should output: "OK: All 13 tools registered."
```

## Upgrading

### From V3 Tier 2 (12 tools) to V3 Tier 3 (13 tools)

The upgrade is safe and non-destructive:

1. **Stop all Claude Code sessions** (to avoid MCP server conflicts during file replacement)
2. **Pull the latest code**: `git pull`
3. **Run the installer**: `python install.py`

What happens:
- All `.py` files are replaced with the latest versions
- `config.yaml` is **preserved** (never overwritten)
- `memory.db` is **backed up** automatically before migration
- Schema migration is **purely additive** (new columns/tables, no deletions)
- Existing hooks are de-duplicated and re-registered
- New files added: `session_init.py`, `register_codex.py`, TUI dashboard

After upgrade:
- MCP server reports 13 tools instead of 12
- New `/tui` and `/consolidate` slash commands available
- CLAUDE.md blocks are updated automatically on next session start

### Rollback

If something goes wrong:
- Your database backup is at `~/.cognilayer/memory.db.backup-YYYYMMDD-HHMMSS`
- Copy it back: `cp ~/.cognilayer/memory.db.backup-* ~/.cognilayer/memory.db`
- Restore old code: `git checkout <previous-commit> && python install.py`

## Usage

### Slash Commands

| Command | Description |
|---------|-------------|
| `/status` | Show memory stats and project context |
| `/recall [query]` | Search memory for specific knowledge |
| `/harvest` | Manually trigger knowledge extraction |
| `/onboard` | Scan current project and build initial memory |
| `/onboard-all` | Batch onboard all projects in your workspace |
| `/forget [query]` | Delete specific facts from memory |
| `/identity` | Manage Project Identity Card |
| `/consolidate` | Run memory consolidation (clusters, tiers, contradictions) |
| `/tui [project]` | Launch TUI dashboard |

### Automatic Behavior

CogniLayer works automatically once installed:
- **Session start**: Injects project DNA and last session bridge into CLAUDE.md
- **During session**: Claude proactively saves important facts to memory
- **File changes**: Every Write/Edit is logged for crash recovery
- **Session end**: Closes session, builds emergency bridge if needed

## Architecture

```
~/.cognilayer/
├── memory.db              # SQLite (WAL mode, FTS5, 17 tables)
├── config.yaml            # Configuration (never overwritten)
├── active_session.json    # Current session state (runtime)
├── mcp-server/
│   ├── server.py          # MCP entry point (13 tools)
│   ├── db.py              # Shared DB helper
│   ├── i18n.py            # Translations (EN + CS)
│   ├── init_db.py         # Schema creation + migration
│   ├── register_codex.py  # Codex CLI registration
│   ├── indexer/           # File scanning and chunking
│   ├── search/            # FTS5 + vector search helpers
│   └── tools/             # 13 MCP tool implementations
├── hooks/
│   ├── on_session_start.py
│   ├── on_session_end.py
│   ├── on_file_change.py
│   ├── generate_agents_md.py  # Codex AGENTS.md generator
│   └── register.py
├── tui/                   # TUI Dashboard (Textual)
│   ├── app.py             # Main application
│   ├── data.py            # Read-only data access layer
│   ├── styles.tcss        # CSS stylesheet
│   ├── screens/           # 7 tab screens
│   └── widgets/           # Reusable widgets
└── logs/
    └── cognilayer.log
```

### Database Schema (17 tables)

| Table | Purpose |
|-------|---------|
| `projects` | Registered projects with DNA |
| `facts` | 14 types of atomic knowledge units |
| `facts_fts` | FTS5 fulltext index on facts |
| `file_chunks` | Indexed project documentation |
| `chunks_fts` | FTS5 fulltext index on chunks |
| `decisions` | Append-only decision log |
| `sessions` | Session records with bridges + episodes |
| `changes` | Automatic file change log |
| `project_identity` | Identity Card (deploy, safety) |
| `identity_audit_log` | Safety field change history |
| `tech_templates` | Reusable tech stack templates |
| `fact_links` | Zettelkasten bidirectional links |
| `knowledge_gaps` | Tracked weak/failed searches |
| `fact_clusters` | Consolidation output clusters |
| `contradictions` | Detected conflicting facts |
| `causal_chains` | Cause → effect relationships |
| `facts_vec` / `chunks_vec` | Vector embeddings (optional) |

## Configuration

Edit `~/.cognilayer/config.yaml`:

```yaml
# Language — "en" (default) or "cs" (Czech)
language: "en"

# Set your projects directory
projects:
  base_path: "~/projects"

# Adjust indexer settings
indexer:
  scan_depth: 3
  chunk_max_chars: 2000

# Search defaults
search:
  default_limit: 5
  max_limit: 10
```

### Language Support

CogniLayer supports English (`en`) and Czech (`cs`). Set the `language` field in `config.yaml` to switch. After changing the language, re-run `python install.py` to update slash commands.

## Known Limitations

- **Concurrent CLIs**: Running Claude Code and Codex CLI simultaneously on the same project may cause session tracking conflicts. Use one CLI at a time per project.
- **PostToolUse tracking**: Codex CLI does not have hooks, so file change tracking (the `changes` table) is not available for Codex sessions.
- **TUI Dashboard**: Requires `textual` package. The TUI is read-only except for resolving contradictions.

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

## License

[GPL-3.0](LICENSE)
