"""Validación de líneas JSONL escritas por el hook.

El archivo de eventos es una entrada no confiable a efectos de robustez:
cualquier línea malformada, demasiado grande o con tipos inesperados se
descarta sin afectar al resto.
"""

from __future__ import annotations

import json
import re
import time

from .models import parse_iso

MAX_LINE_BYTES = 16_384
MAX_STR = 200
ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,128}$")
EVENT_TYPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
KNOWN_EVENTS = {
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "Notification",
    "PermissionRequest",
    "PreCompact",
}
META_KEYS = {
    "source": str,
    "reason": str,
    "notification_type": str,
    "permission_mode": str,
    "duration_ms": (int, float),
    "is_interrupt": bool,
    "stop_hook_active": bool,
    "trigger": str,
    "model": str,
    "cwd": str,
    "effort": str,
    "background_running": int,
    "is_error": bool,
}
ORIGIN_KEYS = {
    "entrypoint": str,
    "cloud": bool,
    "tmux": bool,
    "remote_control": bool,
    "claude_pid": int,
    "claude_start": int,
}


def _id(v) -> str | None:
    return v if isinstance(v, str) and ID_RE.match(v) else None


def _clean(d, schema: dict) -> dict:
    out = {}
    if not isinstance(d, dict):
        return out
    for k, typ in schema.items():
        v = d.get(k)
        if v is None or (typ is not bool and isinstance(v, bool)):
            continue
        if isinstance(v, typ):
            out[k] = v[:MAX_STR] if isinstance(v, str) else v
    return out


def normalize_record(rec, now: float | None = None) -> dict | None:
    """Convierte un dict del JSONL en el evento interno, o None si no es válido."""
    if not isinstance(rec, dict):
        return None
    et = rec.get("event_type")
    if not isinstance(et, str) or not EVENT_TYPE_RE.match(et):
        return None
    eid = _id(rec.get("event_id"))
    if not eid:
        return None
    ts = parse_iso(rec.get("timestamp")) if isinstance(rec.get("timestamp"), str) else None
    now = now if now is not None else time.time()
    if ts is None or ts > now + 300:
        ts = now
    source = rec.get("source") if rec.get("source") in ("hook", "demo") else "hook"
    tool = rec.get("tool_name")
    agent_type = rec.get("agent_type")
    return {
        "event_id": eid,
        "ts": ts,
        "event_type": et,
        "known": et in KNOWN_EVENTS,
        "session_id": _id(rec.get("session_id")),
        "agent_id": _id(rec.get("agent_id")),
        "agent_type": agent_type[:64] if isinstance(agent_type, str) and agent_type else None,
        "tool_name": tool[:64] if isinstance(tool, str) and tool else None,
        "tool_use_id": _id(rec.get("tool_use_id")),
        "source": source,
        "meta": _clean(rec.get("meta"), META_KEYS),
        "origin": _clean(rec.get("origin"), ORIGIN_KEYS),
    }


def normalize_line(line: bytes | str, now: float | None = None) -> dict | None:
    if isinstance(line, str):
        line = line.encode("utf-8", "replace")
    if not line.strip() or len(line) > MAX_LINE_BYTES:
        return None
    try:
        rec = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    return normalize_record(rec, now)
