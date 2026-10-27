"""Convierte eventos observados en estados de entidades.

Módulo puro: no hace E/S. Todas las funciones reciben `now` explícito para
que las transiciones sean deterministas y testeables. La escena del
frontend no contiene ninguna de estas reglas.
"""

from __future__ import annotations

import fnmatch
import os
import uuid
from dataclasses import dataclass

from .layout import assign_desk
from .models import Entity

TOOL_EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"}


@dataclass
class Timing:
    stale_after: float = 300
    idle_after: float = 900
    error_visible: float = 8
    ended_visible: float = 300
    archive_after: float = 3600

    @classmethod
    def from_config(cls, t: dict) -> "Timing":
        return cls(
            stale_after=float(t.get("stale_after_seconds", 300)),
            idle_after=float(t.get("idle_after_seconds", 900)),
            error_visible=float(t.get("error_visible_seconds", 8)),
            ended_visible=float(t.get("ended_visible_seconds", 300)),
            archive_after=float(t.get("archive_after_seconds", 3600)),
        )


@dataclass
class ProcInfo:
    pid: int
    ppid: int
    start_ticks: int
    start_epoch: float
    comm: str
    exe_name: str | None = None
    cwd: str | None = None
    script_name: str | None = None
    is_claude: bool = False
    rc_server: bool = False  # proceso `claude remote-control` (servidor que lanza sesiones)


def _short(s: str | None, n: int = 6) -> str:
    return (s or "?")[:n]


def _fmt_age(sec: float) -> str:
    sec = int(sec)
    if sec < 90:
        return f"{sec} s"
    if sec < 5400:
        return f"{sec // 60} min"
    return f"{sec // 3600} h"


class Office:
    def __init__(self, timing: Timing | None = None, entities: dict[str, Entity] | None = None):
        self.timing = timing or Timing()
        self.entities: dict[str, Entity] = entities or {}
        self.claude_without_hooks = 0
        self.last_process_scan: float | None = None
        self.last_transcript_scan: float | None = None

    # ------------------------------------------------------------------ util
    def _set(self, e: Entity, now: float, status: str, *, detail=None, confidence="high", source=None, reason=""):
        if status != e.status or detail != e.detail:
            e.status_since = now
        e.status = status
        e.detail = detail
        e.confidence = confidence
        if source:
            e.source = source
        e.reason = reason
        e.updated_at = now

    def _place(self, e: Entity) -> None:
        if e.desk is None or e.archived:
            e.desk = assign_desk(self.entities.values(), e)

    def _unarchive(self, e: Entity) -> None:
        if e.archived:
            e.archived = False
            e.desk = None
            self._place(e)

    def _archive(self, e: Entity, now: float) -> None:
        e.archived = True
        e.updated_at = now

    # --------------------------------------------------------------- lookups
    def _ensure_session(self, ev: dict, now: float) -> Entity:
        sid = ev.get("session_id") or "unknown"
        eid = f"s:{sid}"
        e = self.entities.get(eid)
        cwd = ev["meta"].get("cwd")
        if e is None:
            e = Entity(
                id=eid,
                kind="claude_session",
                display_name="",
                session_id=sid if sid != "unknown" else None,
                role="independent",
                started_at=ev["ts"],
                source=ev["source"],
            )
            self.entities[eid] = e
            self._place(e)
        if cwd and not e.cwd:
            e.cwd = cwd
        if ev["source"] in ("hook", "demo"):
            e.has_hooks = True
        o = ev.get("origin") or {}
        if o:
            merged = dict(e.origin)
            for k, v in o.items():
                if k == "remote_control":
                    merged[k] = bool(merged.get(k)) or bool(v)
                elif k in ("claude_pid", "claude_start"):
                    continue
                elif v is not None:
                    merged[k] = v
            e.origin = merged
            if o.get("claude_pid"):
                e.claude_pid = o["claude_pid"]
                e.claude_start = o.get("claude_start")
        name = os.path.basename((e.cwd or "").rstrip("/")) or "sesión"
        e.display_name = f"{name} · {_short(e.session_id)}"
        return e

    def _ensure_subagent(self, session: Entity, agent_id: str, agent_type: str | None, ts: float, source: str) -> Entity:
        eid = f"a:{session.session_id or 'unknown'}:{agent_id}"
        e = self.entities.get(eid)
        if e is None:
            e = Entity(
                id=eid,
                kind="subagent",
                display_name="",
                session_id=session.session_id,
                agent_id=agent_id,
                parent_id=session.id,
                started_at=ts,
                cwd=session.cwd,
                source=source,
                has_hooks=source in ("hook", "demo"),
            )
            self.entities[eid] = e
        if agent_type and not e.agent_type:
            e.agent_type = agent_type
        e.display_name = f"{e.agent_type or 'subagente'} · {_short(agent_id, 5)}"
        self._place(e)
        return e

    def _ensure_unattributed(self, session: Entity, ts: float) -> Entity:
        eid = f"u:{session.session_id or 'unknown'}"
        e = self.entities.get(eid)
        if e is None:
            e = Entity(
                id=eid,
                kind="unattributed",
                display_name=f"no atribuido · {_short(session.session_id)}",
                session_id=session.session_id,
                parent_id=session.id,
                started_at=ts,
                source="hook",
                has_hooks=True,
            )
            self.entities[eid] = e
            self._place(e)
        return e

    def active_children(self, session: Entity) -> list[Entity]:
        return [
            e
            for e in self.entities.values()
            if e.parent_id == session.id and e.kind == "subagent" and not e.ended and not e.archived
        ]

    # ----------------------------------------------------------------- hooks
    def apply(self, ev: dict, now: float | None = None) -> tuple[str, list[Entity]]:
        """Aplica un evento normalizado. Devuelve (entity_id, entidades cambiadas)."""
        now = ev["ts"] if now is None else now
        ts = ev["ts"]
        session = self._ensure_session(ev, now)
        changed = [session]
        et = ev["event_type"]

        if ev.get("agent_id"):
            if et in TOOL_EVENTS:
                session.agent_ids_on_tools = True
            target = self._ensure_subagent(session, ev["agent_id"], ev.get("agent_type"), ts, ev["source"])
            changed.append(target)
        elif et in TOOL_EVENTS and not session.agent_ids_on_tools and self.active_children(session):
            # Versión de Claude Code que no etiqueta las herramientas de los
            # subagentes: no se puede saber quién la usó. No se adivina.
            target = self._ensure_unattributed(session, ts)
            changed.append(target)
        else:
            target = session

        if et not in ("SessionEnd", "SubagentStop"):
            self._unarchive(target)
        if et in ("SessionStart", "UserPromptSubmit") and target.ended:
            target.ended = False
            self._unarchive(target)
        target.last_event_at = max(target.last_event_at or 0, ts)
        target.last_seen_at = target.last_event_at
        target.last_event_type = et
        target.counters["events"] = target.counters.get("events", 0) + 1
        session.last_seen_at = max(session.last_seen_at or 0, ts)
        src = ev["source"]
        meta = ev["meta"]
        tool = ev.get("tool_name")

        def set_(status, **kw):
            kw.setdefault("source", src)
            if target.status == "error" and status != "error" and target.error_until and ts < target.error_until:
                # Periodo mínimo visible del error: se aplaza la transición.
                target.after_error = {"status": status, **kw}
                return
            self._set(target, now, status, **kw)

        if et == "SessionStart":
            set_("waiting", detail="session_start", confidence="medium", reason=f"SessionStart ({meta.get('source', '?')})")
        elif et == "UserPromptSubmit":
            set_("working", detail="prompt", reason="UserPromptSubmit recibido")
        elif et == "PreToolUse":
            target.open_tools[ev.get("tool_use_id") or str(uuid.uuid4())] = {"tool": tool, "ts": ts}
            target.current_tool = tool
            target.counters["tools"] = target.counters.get("tools", 0) + 1
            set_("working", detail="tool", reason=f"PreToolUse: {tool or '?'}")
        elif et in ("PostToolUse", "PostToolUseFailure"):
            target.open_tools.pop(ev.get("tool_use_id") or "", None)
            remaining = list(target.open_tools.values())
            target.current_tool = remaining[-1]["tool"] if remaining else None
            dur = meta.get("duration_ms")
            dur_txt = f" ({int(dur)} ms)" if isinstance(dur, (int, float)) else ""
            if et == "PostToolUseFailure" and meta.get("is_interrupt"):
                set_("waiting", detail="interrupted", reason=f"Herramienta {tool or '?'} interrumpida")
            elif et == "PostToolUseFailure":
                target.counters["errors"] = target.counters.get("errors", 0) + 1
                self._set(target, now, "error", detail="tool_error", source=src, reason=f"PostToolUseFailure: {tool or '?'}{dur_txt}")
                target.error_until = ts + self.timing.error_visible
                target.after_error = None
            elif remaining:
                set_("working", detail="tool", reason=f"PostToolUse: {tool or '?'}{dur_txt}; quedan {len(remaining)} herramienta(s) abiertas")
            else:
                set_("waiting", detail="between_tools", confidence="medium", reason=f"PostToolUse: {tool or '?'} terminada{dur_txt}; turno en curso")
        elif et == "PermissionRequest":
            set_("waiting", detail="needs_permission", reason=f"Pide permiso para {tool or 'una herramienta'}")
        elif et == "Notification":
            nt = meta.get("notification_type")
            if nt == "permission_prompt":
                set_("waiting", detail="needs_permission", reason="Notification: pide permiso")
            elif nt in ("idle_prompt", "elicitation_dialog"):
                set_("waiting", detail="needs_input", reason=f"Notification: espera respuesta ({nt})")
        elif et == "Stop":
            target.open_tools.clear()
            target.current_tool = None
            bg = meta.get("background_running") or 0
            if bg:
                set_("completed", detail="turn_end_bg", reason=f"Stop: fin de turno; {bg} tarea(s) en segundo plano siguen")
            else:
                set_("completed", detail="turn_end", reason="Stop: fin de turno")
        elif et == "SubagentStart":
            set_("working", detail="started", reason="SubagentStart recibido")
        elif et == "SubagentStop":
            target.open_tools.clear()
            target.current_tool = None
            target.ended = True
            set_("completed", detail="subagent_end", reason="SubagentStop recibido")
        elif et == "SessionEnd":
            target.open_tools.clear()
            target.current_tool = None
            target.ended = True
            set_("completed", detail="session_end", reason=f"SessionEnd ({meta.get('reason', '?')})")
            for child in self.entities.values():
                if child.parent_id == session.id and not child.ended:
                    child.ended = True
                    child.open_tools.clear()
                    child.current_tool = None
                    self._set(child, now, "completed", detail="parent_end", confidence="medium", source="derived", reason="La sesión padre terminó")
                    changed.append(child)
        elif et == "PreCompact":
            set_("working", detail="compacting", confidence="medium", reason=f"PreCompact ({meta.get('trigger', '?')})")
        target.updated_at = now
        return target.id, changed

    # ------------------------------------------------------------------ tick
    def tick(self, now: float) -> list[Entity]:
        changed: list[Entity] = []
        t = self.timing
        for e in self.entities.values():
            if e.archived:
                continue
            before = (e.status, e.detail, e.archived)
            if e.status == "error" and e.error_until and now >= e.error_until:
                nxt = e.after_error or {"status": "waiting", "detail": "after_error", "confidence": "medium", "source": "derived", "reason": "Tras un error, sin eventos nuevos"}
                nxt = dict(nxt)
                self._set(e, now, nxt.pop("status"), **nxt)
                e.after_error = None
                e.error_until = None
            if e.source == "demo":
                pass
            elif e.kind == "external_process":
                if e.status == "exited" and now - (now if e.status_since is None else e.status_since) > t.ended_visible:
                    self._archive(e, now)
            elif e.ended:
                if now - (now if e.status_since is None else e.status_since) > t.ended_visible:
                    self._archive(e, now)
            elif e.kind != "external_process" and e.last_event_at is not None:
                age = now - e.last_event_at
                if e.status == "working" and not e.open_tools and age > t.stale_after and e.has_hooks:
                    self._set(e, now, "stale", confidence="low", source="derived", reason=f"Sin eventos desde hace {_fmt_age(age)} (inferencia)")
                elif e.status in ("waiting", "completed") and age > t.idle_after:
                    self._set(e, now, "idle", confidence="low", source="derived", reason=f"Sin actividad observada en {_fmt_age(age)} (no implica pausa)")
                if e.status in ("idle", "stale", "unknown") and age > t.archive_after and not self.active_children(e):
                    self._archive(e, now)
            if (e.status, e.detail, e.archived) != before:
                changed.append(e)
        return changed

    # ------------------------------------------------------------- processes
    def process_scan(self, procs: list[ProcInfo], now: float, allowlist: list[str], min_age: float = 3) -> tuple[list[Entity], list[dict]]:
        self.last_process_scan = now
        changed: list[Entity] = []
        events: list[dict] = []
        by_pid = {p.pid: p for p in procs}
        alive = {(p.pid, p.start_ticks) for p in procs if p.is_claude}
        alive_pids = {p.pid for p in procs if p.is_claude}

        # Liveness de sesiones con PID de claude conocido.
        known_claude: dict[int, Entity] = {}
        for e in self.entities.values():
            if e.kind != "claude_session" or not e.claude_pid:
                continue
            is_alive = (e.claude_pid, e.claude_start) in alive if e.claude_start else e.claude_pid in alive_pids
            if is_alive:
                known_claude[e.claude_pid] = e
            if e.process_alive != is_alive:
                e.process_alive = is_alive
                changed.append(e)
            if not is_alive and not e.ended and not e.archived:
                e.ended = True
                e.open_tools.clear()
                e.current_tool = None
                self._set(e, now, "completed", detail="process_gone", confidence="medium", source="process_monitor", reason=f"El proceso claude (PID {e.claude_pid}) ya no existe; no llegó SessionEnd")
                for child in self.entities.values():
                    if child.parent_id == e.id and not child.ended:
                        child.ended = True
                        self._set(child, now, "completed", detail="parent_end", confidence="medium", source="derived", reason="La sesión padre terminó")
                        changed.append(child)
                changed.append(e)
        self.claude_without_hooks = len(
            [p for p in procs if p.is_claude and not p.rc_server and p.pid not in known_claude and not _has_claude_ancestor(p, by_pid)]
        )

        seen: set[str] = set()
        for p in procs:
            if p.is_claude or not _allowed(p, allowlist):
                continue
            if now - p.start_epoch < min_age:
                continue
            eid = f"p:{p.pid}:{p.start_ticks}"
            seen.add(eid)
            e = self.entities.get(eid)
            if e is None:
                e = Entity(
                    id=eid,
                    kind="external_process",
                    display_name=p.comm + (f" · {p.script_name}" if p.script_name else ""),
                    pid=p.pid,
                    ppid=p.ppid,
                    process_name=p.comm,
                    script_name=p.script_name,
                    cwd=p.cwd,
                    started_at=p.start_epoch,
                    source="process_monitor",
                )
                e.association = self._associate(p, by_pid, known_claude)
                if e.association:
                    e.parent_id = e.association["entity_id"]
                    parent = self.entities.get(e.parent_id)
                    e.session_id = parent.session_id if parent else None
                self.entities[eid] = e
                self._place(e)
                self._set(e, now, "running", confidence="high", source="process_monitor", reason="PID sigue activo")
                changed.append(e)
                events.append(_proc_event("ProcessStart", e, now))
            e.last_seen_at = now
        for e in self.entities.values():
            if e.kind == "external_process" and e.status == "running" and e.id not in seen:
                self._set(e, now, "exited", confidence="high", source="process_monitor", reason="El PID ya no existe")
                e.ended = True
                changed.append(e)
                events.append(_proc_event("ProcessExit", e, now))
        return changed, events

    def _associate(self, p: ProcInfo, by_pid: dict[int, ProcInfo], known_claude: dict[int, Entity]) -> dict | None:
        cur, hops = p.ppid, 0
        while cur and cur > 1 and hops < 32:
            if cur in known_claude:
                s = known_claude[cur]
                return {"entity_id": s.id, "confidence": "high", "reason": f"Proceso descendiente de claude (PID {cur})"}
            nxt = by_pid.get(cur)
            if not nxt:
                break
            cur, hops = nxt.ppid, hops + 1
        if p.cwd:
            cands = [
                e
                for e in self.entities.values()
                if e.kind == "claude_session" and e.cwd and not e.archived and (p.cwd == e.cwd or p.cwd.startswith(e.cwd.rstrip("/") + "/"))
            ]
            if cands:
                s = max(cands, key=lambda e: (len(e.cwd or ""), e.last_seen_at or 0))
                return {"entity_id": s.id, "confidence": "low", "reason": "Asociación probable: mismo directorio de trabajo"}
        return None

    # ------------------------------------------------------------ transcripts
    def transcript_scan(self, found: list[dict], now: float) -> list[Entity]:
        """found: [{session_id, cwd_guess, mtime, subagents:[{agent_id, agent_type, mtime, finished}]}]
        Solo metadatos de archivo: nunca se lee el contenido de la conversación."""
        self.last_transcript_scan = now
        changed: list[Entity] = []
        for f in found:
            eid = f"s:{f['session_id']}"
            e = self.entities.get(eid)
            if e is not None and e.has_hooks:
                # Con hooks, el transcript no decide el estado.
                e.transcript_mtime = f["mtime"]
                continue
            if e is None:
                if now - f["mtime"] > self.timing.archive_after:
                    continue
                e = Entity(
                    id=eid,
                    kind="claude_session",
                    display_name=f"{f.get('cwd_guess') or 'sesión'} · {_short(f['session_id'])}",
                    session_id=f["session_id"],
                    role="independent",
                    started_at=f["mtime"],
                    source="transcript",
                )
                self.entities[eid] = e
                self._place(e)
            before = (e.status, e.detail, e.archived, e.transcript_mtime)
            if e.transcript_mtime != f["mtime"]:
                e.transcript_mtime = e.last_seen_at = e.last_event_at = f["mtime"]
                self._unarchive(e)
            if not e.archived:
                self._transcript_status(e, now, f["mtime"])
            if (e.status, e.detail, e.archived, e.transcript_mtime) != before:
                changed.append(e)
            for sa in f.get("subagents", []):
                aid = f"a:{e.session_id}:{sa['agent_id']}"
                a = self.entities.get(aid)
                if a is None and (sa.get("finished") or now - sa["mtime"] > self.timing.idle_after):
                    continue  # subagentes antiguos o ya terminados: no se resucitan
                if a is not None and a.archived:
                    continue
                a = self._ensure_subagent(e, sa["agent_id"], sa.get("agent_type"), sa["mtime"], "transcript")
                b = (a.status, a.detail)
                a.last_event_at = a.last_seen_at = sa["mtime"]
                if sa.get("finished"):
                    if not a.ended:
                        a.ended = True
                        self._set(a, now, "completed", detail="subagent_end", confidence="medium", source="transcript", reason="Metadatos del subagente: finished")
                else:
                    self._transcript_status(a, now, sa["mtime"])
                if (a.status, a.detail) != b:
                    changed.append(a)
        return changed

    def _transcript_status(self, e: Entity, now: float, mtime: float) -> None:
        age = now - mtime
        if age < 60:
            self._set(e, now, "working", detail="transcript_activity", confidence="low", source="transcript", reason=f"Sin hooks: transcript modificado hace {_fmt_age(age)} (inferencia)")
        elif age < self.timing.idle_after:
            self._set(e, now, "unknown", confidence="low", source="transcript", reason="Sin hooks: no hay datos de estado")
        else:
            self._set(e, now, "idle", confidence="low", source="transcript", reason=f"Sin hooks: transcript sin cambios en {_fmt_age(age)}")


def _allowed(p: ProcInfo, allowlist: list[str]) -> bool:
    names = {p.comm, p.exe_name} - {None}
    return any(fnmatch.fnmatchcase(n, pat) for n in names for pat in allowlist)


def _has_claude_ancestor(p: ProcInfo, by_pid: dict[int, ProcInfo]) -> bool:
    cur, hops = p.ppid, 0
    while cur and cur > 1 and hops < 32:
        q = by_pid.get(cur)
        if not q:
            return False
        if q.is_claude and not q.rc_server:
            return True
        cur, hops = q.ppid, hops + 1
    return False


def _proc_event(kind: str, e: Entity, now: float) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "ts": now,
        "event_type": kind,
        "known": True,
        "session_id": e.session_id,
        "agent_id": None,
        "agent_type": None,
        "tool_name": None,
        "tool_use_id": None,
        "source": "process_monitor",
        "meta": {"pid": e.pid, "process_name": e.process_name},
        "origin": {},
        "entity_id": e.id,
    }
