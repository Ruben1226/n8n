"""Descubre sesiones de Claude Code SIN hooks a partir de los archivos de
~/.claude/projects. Solo usa nombres y fechas de modificación; nunca lee el
contenido de la conversación. De los .meta.json de subagentes solo se
toman `agentType` y `finished`.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

UUID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")
AGENT_RE = re.compile(r"^agent-([A-Za-z0-9_-]{1,64})\.jsonl$")


def projects_dir() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return Path(base) / "projects"


def _guess_name(encoded: str) -> str:
    # El nombre del directorio es el cwd con "/" -> "-"; ambiguo si el nombre
    # tenía guiones, así que solo se usa como etiqueta.
    parts = [p for p in encoded.split("-") if p]
    return parts[-1][:40] if parts else "sesión"


def _meta(path: Path) -> dict:
    try:
        if path.stat().st_size > 65536:
            return {}
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    if isinstance(d.get("agentType"), str):
        out["agent_type"] = d["agentType"][:64]
    if isinstance(d.get("finished"), bool):
        out["finished"] = d["finished"]
    return out


def scan(max_age: float, root: Path | None = None, now: float | None = None) -> list[dict]:
    root = root or projects_dir()
    now = now or time.time()
    found: list[dict] = []
    try:
        projects = list(os.scandir(root))
    except OSError:
        return found
    for proj in projects:
        if not proj.is_dir(follow_symlinks=False):
            continue
        try:
            entries = list(os.scandir(proj.path))
        except OSError:
            continue
        for f in entries:
            if not f.name.endswith(".jsonl") or not f.is_file(follow_symlinks=False):
                continue
            sid = f.name[:-6]
            if not UUID_RE.match(sid):
                continue
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            subagents = []
            sub_dir = Path(proj.path) / sid / "subagents"
            if sub_dir.is_dir():
                try:
                    for s in os.scandir(sub_dir):
                        m = AGENT_RE.match(s.name)
                        if not m:
                            continue
                        smt = s.stat().st_mtime
                        mtime = max(mtime, smt)
                        if now - smt > max_age:
                            continue
                        subagents.append({"agent_id": m.group(1), "mtime": smt, **_meta(sub_dir / f"agent-{m.group(1)}.meta.json")})
                except OSError:
                    pass
            if now - mtime > max_age:
                continue
            found.append({"session_id": sid, "cwd_guess": _guess_name(proj.name), "mtime": mtime, "subagents": subagents})
    return found
