"""Generador de datos sintéticos para el modo DEMO.

Produce eventos con source="demo" que pasan por la misma máquina de estados
que los reales, pero el modo demo usa su propia base de datos (demo.db).
"""

from __future__ import annotations

import random
import uuid

from ..domain.layout import assign_desk
from ..domain.models import Entity

SESSIONS = [
    ("demo-main-0001", "/home/demo/tesis", {"entrypoint": "cli", "tmux": True}),
    ("demo-rc-0002", "/home/demo/analisis", {"entrypoint": "cli", "remote_control": True}),
]
AGENTS = [("ag-explore1", "Explore"), ("ag-review01", "code-reviewer"), ("ag-general1", "general-purpose")]
TOOLS = ["Read", "Grep", "Bash", "Edit", "Glob", "Write", "WebFetch"]
PROCS = [("topas", None), ("python3", "analisis_dosis.py"), ("root", None)]


def _ev(ts: float, et: str, sid: str, **kw) -> dict:
    meta = kw.pop("meta", {})
    return {
        "event_id": str(uuid.uuid4()),
        "ts": ts,
        "event_type": et,
        "known": True,
        "session_id": sid,
        "agent_id": kw.get("agent_id"),
        "agent_type": kw.get("agent_type"),
        "tool_name": kw.get("tool_name"),
        "tool_use_id": kw.get("tool_use_id"),
        "source": "demo",
        "meta": meta,
        "origin": kw.get("origin", {}),
    }


class DemoGenerator:
    """Máquina de pasos simple: cada llamada a step() devuelve eventos nuevos."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.started = False
        self.agent_live: dict[str, bool] = {}
        self.open_tool: dict[str, str | None] = {}
        self._tool_of: dict[str, str] = {}

    def initial(self, now: float) -> list[dict]:
        self.started = True
        out = []
        for sid, cwd, origin in SESSIONS:
            out.append(_ev(now, "SessionStart", sid, meta={"source": "startup", "cwd": cwd}, origin=origin))
            out.append(_ev(now, "UserPromptSubmit", sid))
        return out

    def processes(self, office, now: float) -> list[Entity]:
        changed = []
        for i, (name, script) in enumerate(PROCS):
            eid = f"p:demo:{i}"
            if eid in office.entities:
                continue
            parent = office.entities.get(f"s:{SESSIONS[i % 2][0]}")
            e = Entity(
                id=eid,
                kind="external_process",
                display_name=name + (f" · {script}" if script else ""),
                process_name=name,
                script_name=script,
                pid=40000 + i,
                session_id=parent.session_id if parent else None,
                parent_id=parent.id if parent else None,
                association={"entity_id": parent.id, "confidence": "high", "reason": "DEMO"} if parent else None,
                started_at=now,
                status="running",
                confidence="high",
                source="demo",
                reason="DEMO: proceso ficticio",
                status_since=now,
                updated_at=now,
                last_seen_at=now,
            )
            e.desk = assign_desk(office.entities.values(), e)
            office.entities[eid] = e
            changed.append(e)
        return changed

    def step(self, now: float) -> list[dict]:
        if not self.started:
            return self.initial(now)
        r = self.rng
        sid = r.choice(SESSIONS)[0]
        actor_key = sid
        kw: dict = {}
        if sid == SESSIONS[0][0] and r.random() < 0.6:
            aid, atype = r.choice(AGENTS)
            if not self.agent_live.get(aid):
                self.agent_live[aid] = True
                return [_ev(now, "SubagentStart", sid, agent_id=aid, agent_type=atype)]
            kw = {"agent_id": aid, "agent_type": atype}
            actor_key = aid
            if r.random() < 0.08:
                self.agent_live[aid] = False
                self.open_tool[aid] = None
                return [_ev(now, "SubagentStop", sid, **kw)]
        open_id = self.open_tool.get(actor_key)
        if open_id:
            self.open_tool[actor_key] = None
            if r.random() < 0.1:
                return [_ev(now, "PostToolUseFailure", sid, tool_use_id=open_id, tool_name="Bash", meta={"is_error": True, "duration_ms": 300}, **kw)]
            return [_ev(now, "PostToolUse", sid, tool_use_id=open_id, tool_name=self._tool_of.get(open_id, "Read"), meta={"duration_ms": r.randint(20, 4000)}, **kw)]
        roll = r.random()
        if not kw and roll < 0.12:
            return [_ev(now, "Stop", sid)]
        if not kw and roll < 0.18:
            return [_ev(now, "UserPromptSubmit", sid)]
        if not kw and roll < 0.22:
            return [_ev(now, "Notification", sid, meta={"notification_type": "permission_prompt"})]
        tid = f"demo_{uuid.uuid4().hex[:12]}"
        tool = r.choice(TOOLS)
        self._tool_of[tid] = tool
        self.open_tool[actor_key] = tid
        return [_ev(now, "PreToolUse", sid, tool_use_id=tid, tool_name=tool, **kw)]
