"""Entidades tipadas y estados normalizados."""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass, field, fields

KINDS = ("claude_session", "subagent", "unattributed", "external_process")
STATUSES = ("working", "waiting", "completed", "error", "idle", "running", "exited", "unknown", "stale")
SOURCES = ("hook", "process_monitor", "transcript", "derived", "demo")
CONFIDENCES = ("high", "medium", "low")


def iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(s: str) -> float | None:
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError, TypeError):
        return None


@dataclass
class Entity:
    id: str
    kind: str
    display_name: str
    session_id: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    parent_id: str | None = None  # id de entidad padre (sesión) para subagentes
    role: str | None = None  # claude_session: main | independent
    cwd: str | None = None
    origin: dict = field(default_factory=dict)  # entrypoint, cloud, tmux, remote_control
    # Proceso
    pid: int | None = None
    ppid: int | None = None
    process_name: str | None = None
    script_name: str | None = None
    association: dict | None = None  # {entity_id, confidence, reason}
    claude_pid: int | None = None
    claude_start: int | None = None
    process_alive: bool | None = None
    # Tiempos (epoch s)
    started_at: float | None = None
    last_seen_at: float | None = None
    last_event_at: float | None = None
    last_event_type: str | None = None
    # Estado
    status: str = "unknown"
    detail: str | None = None
    confidence: str = "low"
    source: str = "derived"
    reason: str = ""
    status_since: float | None = None
    updated_at: float | None = None
    current_tool: str | None = None
    open_tools: dict = field(default_factory=dict)  # tool_use_id -> {tool, ts}
    error_until: float | None = None
    after_error: dict | None = None
    ended: bool = False
    archived: bool = False
    has_hooks: bool = False
    agent_ids_on_tools: bool = False
    transcript_mtime: float | None = None
    counters: dict = field(default_factory=lambda: {"tools": 0, "errors": 0, "events": 0})
    desk: dict | None = None  # {zone, slot}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_public(self) -> dict:
        d = self.to_dict()
        d.pop("after_error", None)
        d["open_tools"] = len(self.open_tools)
        for k in ("started_at", "last_seen_at", "last_event_at", "status_since", "updated_at", "error_until", "transcript_mtime"):
            d[k] = iso(d[k])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Entity":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})
