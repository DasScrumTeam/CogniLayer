"""session_init — MCP tool replacing SessionStart hook for Codex CLI.

Does the same work as on_session_start.py but as an MCP tool call:
1. Detects project from CWD (or provided path)
2. Registers project if new
3. Checks crash recovery
4. Auto-detects identity
5. Generates/loads DNA
6. Loads latest bridge
7. Creates session
8. Returns full context (DNA + bridge + crash info)

No file injection — Codex reads AGENTS.md separately.
"""

import sys
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

# Import session start helpers
sys.path.insert(0, str(COGNILAYER_HOME / "hooks"))
sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))

from i18n import t


def session_init(project_path: str | None = None) -> str:
    """Initialize a CogniLayer session and return full context."""
    from on_session_start import (
        detect_project, register_project_if_new, check_crash_recovery,
        auto_detect_identity, get_or_generate_dna, get_latest_bridge,
        create_session, write_active_session, open_db
    )

    if not DB_PATH.exists():
        return t("session_init.no_db")

    if project_path:
        path = Path(project_path).resolve()
    else:
        path = Path.cwd()

    if not path.exists():
        return t("session_init.invalid_path", path=str(path))

    project_name = detect_project(path)

    db = open_db()
    try:
        register_project_if_new(db, project_name, path)
        crash_info = check_crash_recovery(db, project_name)
        auto_detect_identity(db, project_name, path)
        dna = get_or_generate_dna(db, project_name, path)
        bridge = get_latest_bridge(db, project_name)
        session_id = create_session(db, project_name)
        write_active_session(session_id, project_name, str(path))

        # Re-index if possible (non-critical)
        try:
            from indexer.file_indexer import reindex_project
            reindex_project(db, project_name, path, time_budget=2.0)
        except Exception:
            pass

        db.commit()
    except Exception as e:
        db.close()
        return t("session_init.error", error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass

    # Build response
    parts = [t("session_init.header", project=project_name, session_id=session_id)]
    parts.append("")
    parts.append(dna)

    if bridge:
        parts.append("")
        parts.append(f"## Last Session Bridge\n{bridge}")

    if crash_info:
        parts.append("")
        parts.append(crash_info)

    parts.append("")
    parts.append(t("session_init.instructions"))

    return "\n".join(parts)
