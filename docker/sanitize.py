"""Content sanitization for CogniLayer DB -> CLAUDE.md trust boundary.

This module sits between SQLite reads and CLAUDE.md injection.
It strips patterns that could be used for prompt injection when
DB content (DNA, bridges, facts) is written into instruction files.
"""

import hashlib
import re
from pathlib import Path

# Patterns that should never appear in injected content.
# These are instruction-override patterns commonly used in prompt injection.
_INJECTION_PATTERNS = [
    # Direct instruction overrides
    re.compile(r"(?i)(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?|context)"),
    # Role reassignment
    re.compile(r"(?i)you\s+are\s+now\s+(a|an)\s+"),
    re.compile(r"(?i)from\s+now\s+on[,.]?\s+(you|act|behave|respond)"),
    re.compile(r"(?i)new\s+(system\s+)?instructions?:"),
    re.compile(r"(?i)system\s*prompt\s*:"),
    # Instruction injection delimiters
    re.compile(r"(?i)<\s*/?system[_-]?(prompt|instruction|message)\s*>"),
    re.compile(r"(?i)\[SYSTEM\]"),
    re.compile(r"(?i)\[INST\]"),
    # Data exfiltration commands
    re.compile(r"(?i)(curl|wget|fetch|nc|netcat)\s+https?://"),
    re.compile(r"(?i)(send|post|upload|exfiltrate)\s+(to|data|this|everything)\s"),
    # Base64/encoding obfuscation (long base64 strings are suspicious in DNA/bridges)
    re.compile(r"[A-Za-z0-9+/]{60,}={0,2}"),
]

# Maximum lengths for injected content (defense in depth)
MAX_DNA_LENGTH = 2000
MAX_BRIDGE_LENGTH = 4000
MAX_LINE_LENGTH = 500

# HMAC key file for DB integrity verification
_HMAC_KEY_PATH = Path.home() / ".cognilayer" / ".hmac_key"


def sanitize_for_claude_md(content: str, label: str = "content",
                           max_length: int = 4000) -> str:
    """Sanitize content from DB before injecting into CLAUDE.md.

    Args:
        content: Raw content from SQLite database.
        label: Human-readable label for warnings (e.g., "DNA", "bridge").
        max_length: Maximum allowed length.

    Returns:
        Sanitized content safe for CLAUDE.md injection.
        Returns "[BLOCKED]" marker if content is entirely suspicious.
    """
    if not content:
        return ""

    # Length cap
    if len(content) > max_length:
        content = content[:max_length] + f"\n[truncated {label}: exceeded {max_length} chars]"

    # Check each line
    clean_lines = []
    blocked_count = 0
    for line in content.split("\n"):
        # Truncate excessively long lines
        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH] + "..."

        # Check against injection patterns
        blocked = False
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(line):
                blocked = True
                blocked_count += 1
                break

        if not blocked:
            clean_lines.append(line)

    # If most lines were blocked, the entire content is suspicious
    total = len(clean_lines) + blocked_count
    if total > 0 and blocked_count / total > 0.5:
        return f"[BLOCKED: {label} contained suspicious content ({blocked_count} lines removed)]"

    if blocked_count > 0:
        clean_lines.append(f"[sanitized: {blocked_count} suspicious line(s) removed from {label}]")

    return "\n".join(clean_lines)


def sanitize_dna(dna: str) -> str:
    """Sanitize project DNA before CLAUDE.md injection."""
    return sanitize_for_claude_md(dna, label="DNA", max_length=MAX_DNA_LENGTH)


def sanitize_bridge(bridge: str) -> str:
    """Sanitize session bridge before CLAUDE.md injection."""
    return sanitize_for_claude_md(bridge, label="bridge", max_length=MAX_BRIDGE_LENGTH)


def sanitize_session_id(session_id: str) -> str:
    """Sanitize session ID to prevent path traversal.

    Only allows alphanumeric characters, hyphens, and underscores.
    Returns a safe fallback if the ID contains path separators or other special chars.
    """
    if not session_id:
        return ""
    # UUIDs and Claude session IDs should only contain [a-zA-Z0-9_-]
    if re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        return session_id
    # Suspicious session ID -- hash it to get a safe filename
    return "sanitized-" + hashlib.sha256(session_id.encode()).hexdigest()[:16]


def verify_path_within(path: Path, root: Path) -> bool:
    """Verify that a resolved path stays within the expected root directory.

    Prevents symlink and path traversal attacks.
    """
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
        return str(resolved).startswith(str(root_resolved) + "/") or resolved == root_resolved
    except (OSError, ValueError):
        return False
