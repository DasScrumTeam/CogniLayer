# CogniLayer Secure Container — Hybrid Mode
#
# Runs the MCP server in isolation. Hooks run on the host.
# Both share the same SQLite DB via bind mount (~/.cognilayer -> /data).
#
# Security:
# - Non-root user (UID 10001)
# - Read-only filesystem (except /data bind mount and /tmp tmpfs)
# - No network access (enforced by docker-compose network_mode: none)
# - Minimal attack surface (pip removed after install)

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    COGNILAYER_DATA_DIR=/data

# tini for proper signal handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Non-root user
RUN groupadd -g 10001 cognilayer && \
    useradd -u 10001 -g cognilayer -s /usr/sbin/nologin -M cognilayer

# Python deps (cached layer)
COPY docker/requirements-docker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Application code (root-owned, read-only)
COPY --chown=root:root mcp-server/ /opt/cognilayer/mcp-server/
COPY --chown=root:root config.yaml /opt/cognilayer/config.yaml
COPY --chown=root:root VERSION /opt/cognilayer/VERSION

# Entrypoint wrapper that patches DB_PATH to use COGNILAYER_DATA_DIR
RUN printf '#!/usr/bin/env python3\n\
"""Entrypoint wrapper — patches db.py paths to use /data bind mount."""\n\
import os, sys\n\
data_dir = os.environ.get("COGNILAYER_DATA_DIR", "")\n\
if data_dir:\n\
    from pathlib import Path\n\
    sys.path.insert(0, "/opt/cognilayer/mcp-server")\n\
    import db\n\
    db.COGNILAYER_HOME = Path(data_dir)\n\
    db.DB_PATH = Path(data_dir) / "memory.db"\n\
# Now run the actual server\n\
exec(open("/opt/cognilayer/mcp-server/server.py").read())\n' \
    > /opt/cognilayer/entrypoint.py && \
    chmod 755 /opt/cognilayer/entrypoint.py

RUN mkdir -p /data && chown cognilayer:cognilayer /data

# Remove pip
RUN pip uninstall -y pip setuptools 2>/dev/null; true

USER cognilayer
WORKDIR /opt/cognilayer

HEALTHCHECK --interval=60s --timeout=5s --retries=2 \
    CMD ["python", "entrypoint.py", "--test"]

ENTRYPOINT ["tini", "--"]
CMD ["python", "entrypoint.py"]
