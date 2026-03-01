"""CogniLayer TUI — Read-only data access layer for memory.db."""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".cognilayer" / "memory.db"


def _open() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = sqlite3.Row
    return db


def get_stats(project: str | None = None) -> dict:
    """Get overview statistics."""
    db = _open()
    try:
        where = "WHERE project = ?" if project else ""
        params = (project,) if project else ()

        facts_count = db.execute(
            f"SELECT COUNT(*) FROM facts {where}", params
        ).fetchone()[0]

        hot = db.execute(
            f"SELECT COUNT(*) FROM facts {where + (' AND' if where else 'WHERE')} heat_score >= 0.7",
            params
        ).fetchone()[0]

        warm = db.execute(
            f"SELECT COUNT(*) FROM facts {where + (' AND' if where else 'WHERE')} heat_score >= 0.3 AND heat_score < 0.7",
            params
        ).fetchone()[0]

        cold = facts_count - hot - warm

        sessions_count = db.execute(
            f"SELECT COUNT(*) FROM sessions {where}", params
        ).fetchone()[0]

        changes_count = db.execute(
            f"SELECT COUNT(*) FROM changes {where}", params
        ).fetchone()[0]

        projects_count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

        gaps_count = db.execute(
            f"SELECT COUNT(*) FROM knowledge_gaps {where + (' AND' if where else 'WHERE')} resolved = 0",
            params
        ).fetchone()[0]

        contradictions_count = db.execute(
            f"SELECT COUNT(*) FROM contradictions {where + (' AND' if where else 'WHERE')} resolved = 0",
            params
        ).fetchone()[0]

        # Last session
        last_session = db.execute(
            f"SELECT start_time, bridge_content, episode_title, outcome FROM sessions {where} ORDER BY start_time DESC LIMIT 1",
            params
        ).fetchone()

        return {
            "facts": facts_count,
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "sessions": sessions_count,
            "changes": changes_count,
            "projects": projects_count,
            "gaps": gaps_count,
            "contradictions": contradictions_count,
            "last_session": dict(last_session) if last_session else None,
        }
    finally:
        db.close()


def get_projects() -> list[str]:
    """Get list of project names."""
    db = _open()
    try:
        rows = db.execute("SELECT name FROM projects ORDER BY last_session DESC").fetchall()
        return [r[0] for r in rows]
    finally:
        db.close()


def get_facts(project: str | None = None, type_filter: str | None = None,
              domain_filter: str | None = None, tier_filter: str | None = None,
              search: str | None = None, limit: int = 200) -> list[dict]:
    """Get facts with optional filters."""
    db = _open()
    try:
        conditions = []
        params = []
        if project:
            conditions.append("f.project = ?")
            params.append(project)
        if type_filter:
            conditions.append("f.type = ?")
            params.append(type_filter)
        if domain_filter:
            conditions.append("f.domain = ?")
            params.append(domain_filter)
        if tier_filter:
            conditions.append("f.knowledge_tier = ?")
            params.append(tier_filter)
        if search:
            conditions.append("f.content LIKE ?")
            params.append(f"%{search}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)

        rows = db.execute(f"""
            SELECT f.id, f.project, f.content, f.type, f.domain, f.heat_score,
                   f.knowledge_tier, f.timestamp, f.retrieval_count, f.tags
            FROM facts f
            {where}
            ORDER BY f.heat_score DESC
            LIMIT ?
        """, params).fetchall()

        return [dict(r) for r in rows]
    finally:
        db.close()


def get_fact_types(project: str | None = None) -> list[str]:
    """Get distinct fact types."""
    db = _open()
    try:
        where = "WHERE project = ?" if project else ""
        params = (project,) if project else ()
        rows = db.execute(
            f"SELECT DISTINCT type FROM facts {where} ORDER BY type", params
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        db.close()


def get_fact_domains(project: str | None = None) -> list[str]:
    """Get distinct fact domains."""
    db = _open()
    try:
        where = "WHERE project = ? AND domain IS NOT NULL" if project else "WHERE domain IS NOT NULL"
        params = (project,) if project else ()
        rows = db.execute(
            f"SELECT DISTINCT domain FROM facts {where} ORDER BY domain", params
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        db.close()


def get_heat_distribution(project: str | None = None) -> dict:
    """Get heat score distribution by type."""
    db = _open()
    try:
        where = "WHERE project = ?" if project else ""
        params = (project,) if project else ()

        rows = db.execute(f"""
            SELECT type,
                   COUNT(*) as total,
                   SUM(CASE WHEN heat_score >= 0.7 THEN 1 ELSE 0 END) as hot,
                   SUM(CASE WHEN heat_score >= 0.3 AND heat_score < 0.7 THEN 1 ELSE 0 END) as warm,
                   SUM(CASE WHEN heat_score < 0.3 THEN 1 ELSE 0 END) as cold,
                   AVG(heat_score) as avg_heat
            FROM facts
            {where}
            GROUP BY type
            ORDER BY avg_heat DESC
        """, params).fetchall()

        return [dict(r) for r in rows]
    finally:
        db.close()


def get_heat_by_project() -> list[dict]:
    """Get heat distribution grouped by project."""
    db = _open()
    try:
        rows = db.execute("""
            SELECT project,
                   COUNT(*) as total,
                   SUM(CASE WHEN heat_score >= 0.7 THEN 1 ELSE 0 END) as hot,
                   SUM(CASE WHEN heat_score >= 0.3 AND heat_score < 0.7 THEN 1 ELSE 0 END) as warm,
                   SUM(CASE WHEN heat_score < 0.3 THEN 1 ELSE 0 END) as cold,
                   AVG(heat_score) as avg_heat
            FROM facts
            GROUP BY project
            ORDER BY avg_heat DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_clusters(project: str | None = None) -> list[dict]:
    """Get fact clusters with member facts."""
    db = _open()
    try:
        where = "WHERE c.project = ?" if project else ""
        params = (project,) if project else ()

        clusters = db.execute(f"""
            SELECT c.id, c.project, c.label, c.summary, c.fact_count, c.created
            FROM fact_clusters c
            {where}
            ORDER BY c.fact_count DESC
        """, params).fetchall()

        result = []
        for c in clusters:
            members = db.execute("""
                SELECT id, substr(content, 1, 80) as preview, type, heat_score
                FROM facts WHERE cluster_id = ?
                ORDER BY heat_score DESC LIMIT 20
            """, (c["id"],)).fetchall()
            result.append({
                **dict(c),
                "members": [dict(m) for m in members],
            })

        return result
    finally:
        db.close()


def get_sessions(project: str | None = None, limit: int = 50) -> list[dict]:
    """Get session timeline."""
    db = _open()
    try:
        where = "WHERE s.project = ?" if project else ""
        params = list((project,)) if project else []
        params.append(limit)

        rows = db.execute(f"""
            SELECT s.id, s.project, s.start_time, s.end_time, s.summary,
                   s.bridge_content, s.episode_title, s.episode_tags, s.outcome,
                   s.facts_count, s.changes_count
            FROM sessions s
            {where}
            ORDER BY s.start_time DESC
            LIMIT ?
        """, params).fetchall()

        return [dict(r) for r in rows]
    finally:
        db.close()


def get_gaps(project: str | None = None) -> list[dict]:
    """Get knowledge gaps."""
    db = _open()
    try:
        where = "WHERE project = ?" if project else ""
        params = (project,) if project else ()

        rows = db.execute(f"""
            SELECT id, project, query, hit_count, best_score,
                   first_seen, last_seen, times_seen, resolved
            FROM knowledge_gaps
            {where}
            ORDER BY resolved ASC, times_seen DESC
        """, params).fetchall()

        return [dict(r) for r in rows]
    finally:
        db.close()


def get_contradictions(project: str | None = None) -> list[dict]:
    """Get contradictions."""
    db = _open()
    try:
        where = "WHERE c.project = ?" if project else ""
        params = (project,) if project else ()

        rows = db.execute(f"""
            SELECT c.id, c.project, c.reason, c.detected, c.resolved,
                   fa.content as fact_a_content, fa.type as fact_a_type,
                   fb.content as fact_b_content, fb.type as fact_b_type
            FROM contradictions c
            LEFT JOIN facts fa ON c.fact_id_a = fa.id
            LEFT JOIN facts fb ON c.fact_id_b = fb.id
            {where}
            ORDER BY c.resolved ASC, c.detected DESC
        """, params).fetchall()

        return [dict(r) for r in rows]
    finally:
        db.close()


def resolve_contradiction(contradiction_id: int):
    """Mark a contradiction as resolved."""
    db = _open()
    try:
        db.execute("UPDATE contradictions SET resolved = 1 WHERE id = ?", (contradiction_id,))
        db.commit()
    finally:
        db.close()
