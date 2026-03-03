"""Shared DB helper for CogniLayer. Used by MCP server, hooks, and scripts."""

import sqlite3
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

# Cache: None = not checked, True = available, False = not available
_vec_system_available = None


def get_db_path() -> Path:
    return DB_PATH


def open_db_fast() -> sqlite3.Connection:
    """Fast-path DB open for hooks (no logging, no vec). All PRAGMAs consistent with open_db."""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA wal_autocheckpoint=1000")
    db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = sqlite3.Row
    return db


def open_db(with_vec: bool = False) -> sqlite3.Connection:
    """Open DB with WAL mode + busy_timeout for multi-CLI safety.

    Args:
        with_vec: Load sqlite-vec extension. Only needed for vector search/write.
    """
    import logging, time as _t
    _log = logging.getLogger("cognilayer.db")
    _t0 = _t.time()
    _log.info("open_db: connecting to %s", DB_PATH)
    db = sqlite3.connect(str(DB_PATH))
    _log.info("open_db: connected in %.3fs, setting PRAGMAs", _t.time() - _t0)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA wal_autocheckpoint=1000")
    db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = sqlite3.Row
    _log.info("open_db: PRAGMAs done in %.3fs", _t.time() - _t0)
    if with_vec:
        _load_sqlite_vec(db)
    return db


def _trace_db(msg):
    """Unbuffered trace to file for debugging."""
    from datetime import datetime
    try:
        trace_file = COGNILAYER_HOME / "logs" / "trace.log"
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} [db] {msg}\n")
    except Exception:
        pass


def ensure_vec(db: sqlite3.Connection) -> bool:
    """Ensure sqlite-vec is loaded on this connection. Returns True if available.

    Safe to call multiple times — uses module-level cache to avoid
    repeated ImportError exceptions when sqlite-vec is not installed.
    """
    global _vec_system_available

    _trace_db(f"ensure_vec: _vec_system_available={_vec_system_available}")

    # Fast path: already know it's not available on this system
    if _vec_system_available is False:
        _trace_db("ensure_vec: fast path False")
        return False

    # Check if already loaded on this connection
    _trace_db("ensure_vec: trying SELECT vec_version()")
    try:
        db.execute("SELECT vec_version()")
        _vec_system_available = True
        _trace_db("ensure_vec: vec already loaded, True")
        return True
    except Exception as e:
        _trace_db(f"ensure_vec: vec_version failed: {e}")

    # Try loading
    _trace_db("ensure_vec: calling _load_sqlite_vec")
    return _load_sqlite_vec(db)


def _load_sqlite_vec(db: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension if available. Returns True on success."""
    global _vec_system_available

    _trace_db("_load_sqlite_vec: attempting load")
    try:
        # Load vec0 extension directly by path instead of `import sqlite_vec`
        # which can hang in MCP server context on Windows (numpy import in
        # sqlite_vec.__init__.py blocks when stdin/stdout are MCP pipes).
        vec_dir = Path(__file__).parent.parent
        # Check common install locations for vec0.dll
        import importlib.util
        spec = importlib.util.find_spec("sqlite_vec")
        if spec is None:
            _vec_system_available = False
            _trace_db("_load_sqlite_vec: find_spec=None, not installed")
            return False

        # Load the DLL directly without importing the Python wrapper
        vec0_path = Path(spec.origin).parent / "vec0"
        _trace_db(f"_load_sqlite_vec: loading extension from {vec0_path}")
        db.enable_load_extension(True)
        db.load_extension(str(vec0_path))
        db.enable_load_extension(False)
        _vec_system_available = True
        _trace_db("_load_sqlite_vec: loaded OK via direct path")
        return True
    except ImportError:
        _vec_system_available = False
        _trace_db("_load_sqlite_vec: ImportError, not installed")
        return False
    except Exception as e:
        _vec_system_available = False
        _trace_db(f"_load_sqlite_vec: error: {e}")
        return False
