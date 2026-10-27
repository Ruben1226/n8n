import copy

from backend.domain.state_machine import Office, ProcInfo, Timing
from conftest import hook_events

SID = "65f5ab18-145f-5123-8d1f-9d422d3b358e"
AID = "a0d5980ec0cf098e7"


def replay(events, office=None):
    office = office or Office(Timing())
    trace = []
    for ev in events:
        eid, _ = office.apply(ev)
        e = office.entities[eid]
        trace.append((ev["event_type"], eid, e.status, e.detail))
    return office, trace


def ev(et, ts, sid="s1", **kw):
    return {
        "event_id": f"{et}-{ts}-{kw.get('agent_id')}-{kw.get('tool_use_id')}",
        "ts": ts,
        "event_type": et,
        "known": True,
        "session_id": sid,
        "agent_id": kw.get("agent_id"),
        "agent_type": kw.get("agent_type"),
        "tool_name": kw.get("tool_name"),
        "tool_use_id": kw.get("tool_use_id"),
        "source": kw.get("source", "hook"),
        "meta": kw.get("meta", {}),
        "origin": kw.get("origin", {}),
    }


def test_real_session_replay():
    office, trace = replay(hook_events())
    s = f"s:{SID}"
    a = f"a:{SID}:{AID}"
    assert trace[0] == ("SessionStart", s, "waiting", "session_start")
    assert trace[1] == ("UserPromptSubmit", s, "working", "prompt")
    assert trace[2] == ("PreToolUse", s, "working", "tool")
    assert trace[3] == ("PostToolUse", s, "waiting", "between_tools")
    assert trace[5][0] == "PostToolUseFailure" and trace[5][2] == "error"
    # Herramientas del subagente atribuidas a su entidad (agent_id real)
    sub = [t for t in trace if t[1] == a]
    assert [t[0] for t in sub] == ["SubagentStart", "PreToolUse", "PostToolUse", "SubagentStop"]
    assert office.entities[a].ended and office.entities[a].status == "completed"
    assert office.entities[a].agent_type == "general-purpose"
    assert office.entities[a].parent_id == s
    assert office.entities[s].agent_ids_on_tools
    assert trace[-1] == ("SessionEnd", s, "completed", "session_end")
    assert office.entities[s].ended
    assert office.entities[s].origin["remote_control"] is True
    assert office.entities[s].display_name.startswith("proj · ")
    assert office.entities[s].counters["errors"] == 1


def test_replay_is_deterministic():
    evs = hook_events()
    o1, t1 = replay(copy.deepcopy(evs))
    o2, t2 = replay(copy.deepcopy(evs))
    assert t1 == t2
    assert {k: v.to_dict() for k, v in o1.entities.items()} == {k: v.to_dict() for k, v in o2.entities.items()}


def test_error_has_minimum_visible_time():
    o = Office(Timing(error_visible=8))
    o.apply(ev("PreToolUse", 100, tool_name="Bash", tool_use_id="t1"))
    o.apply(ev("PostToolUseFailure", 101, tool_name="Bash", tool_use_id="t1", meta={"is_error": True}))
    o.apply(ev("PreToolUse", 102, tool_name="Read", tool_use_id="t2"))
    s = o.entities["s:s1"]
    assert s.status == "error"  # transición aplazada
    o.tick(110)
    assert s.status == "working" and s.detail == "tool"


def test_interrupt_is_not_error():
    o = Office()
    o.apply(ev("PreToolUse", 1, tool_name="Bash", tool_use_id="t1"))
    o.apply(ev("PostToolUseFailure", 2, tool_name="Bash", tool_use_id="t1", meta={"is_interrupt": True}))
    assert o.entities["s:s1"].status == "waiting" and o.entities["s:s1"].detail == "interrupted"


def test_permission_and_notifications_need_attention():
    o = Office()
    o.apply(ev("PermissionRequest", 1, tool_name="Bash"))
    assert o.entities["s:s1"].detail == "needs_permission"
    o.apply(ev("Notification", 2, meta={"notification_type": "idle_prompt"}))
    assert o.entities["s:s1"].detail == "needs_input"
    o.apply(ev("Notification", 3, meta={"notification_type": "auth_success"}))
    assert o.entities["s:s1"].detail == "needs_input"  # notificación informativa: sin cambio


def test_stale_and_idle_are_inferred_and_open_tools_block_stale():
    t = Timing(stale_after=60, idle_after=120, archive_after=1000)
    o = Office(t)
    o.apply(ev("UserPromptSubmit", 0))
    o.tick(61)
    s = o.entities["s:s1"]
    assert s.status == "stale" and s.source == "derived" and s.confidence == "low"
    o2 = Office(t)
    o2.apply(ev("PreToolUse", 0, tool_name="Bash", tool_use_id="long"))
    o2.tick(500)
    assert o2.entities["s:s1"].status == "working"  # herramienta larga en curso
    o.apply(ev("Stop", 100))
    o.tick(230)
    assert s.status == "idle" and s.source == "derived"
    o.tick(1200)
    assert s.archived


def test_ended_entities_archive_after_visible_period():
    o = Office(Timing(ended_visible=10))
    o.apply(ev("SubagentStart", 0, agent_id="ag1", agent_type="Explore"))
    o.apply(ev("SubagentStop", 1, agent_id="ag1", agent_type="Explore"))
    a = o.entities["a:s1:ag1"]
    o.tick(5)
    assert not a.archived
    o.tick(20)
    assert a.archived


def test_unattributed_when_version_lacks_agent_ids():
    o = Office()
    o.apply(ev("SubagentStart", 0, agent_id="ag1"))
    eid, _ = o.apply(ev("PreToolUse", 1, tool_name="Read", tool_use_id="t"))
    assert eid == "u:s1"  # no se adivina quién usó la herramienta
    o.apply(ev("PreToolUse", 2, agent_id="ag1", tool_name="Read", tool_use_id="t2"))
    eid, _ = o.apply(ev("PreToolUse", 3, tool_name="Grep", tool_use_id="t3"))
    assert eid == "s:s1"  # la versión sí etiqueta: ausencia de agent_id = sesión


def test_session_end_closes_children():
    o = Office()
    o.apply(ev("SubagentStart", 0, agent_id="ag1"))
    o.apply(ev("SessionEnd", 1, meta={"reason": "logout"}))
    assert o.entities["a:s1:ag1"].ended and o.entities["a:s1:ag1"].detail == "parent_end"


def test_resumed_session_reactivates():
    o = Office(Timing(ended_visible=1))
    o.apply(ev("SessionEnd", 0))
    o.tick(5)
    assert o.entities["s:s1"].archived
    o.apply(ev("SessionStart", 10, meta={"source": "resume"}))
    s = o.entities["s:s1"]
    assert not s.archived and not s.ended and s.desk is not None


def test_stable_desks():
    o = Office()
    for i in range(3):
        o.apply(ev("SessionStart", i, sid=f"s{i}"))
    slots = [o.entities[f"s:s{i}"].desk for i in range(3)]
    assert slots == [{"zone": "coordination", "slot": i} for i in range(3)]
    o.apply(ev("PreToolUse", 5, sid="s1", tool_name="Read", tool_use_id="x"))
    assert o.entities["s:s1"].desk == {"zone": "coordination", "slot": 1}


def test_review_agents_go_to_review_room():
    o = Office()
    o.apply(ev("SubagentStart", 0, agent_id="r1", agent_type="code-reviewer"))
    assert o.entities["a:s1:r1"].desk["zone"] == "review"


# ------------------------------------------------------------- processes
def proc(pid, ppid, comm, start=100, cwd=None, is_claude=False, rc=False):
    return ProcInfo(pid=pid, ppid=ppid, start_ticks=start, start_epoch=0, comm=comm, exe_name=comm, cwd=cwd, is_claude=is_claude, rc_server=rc)


def test_process_detection_association_and_exit():
    o = Office()
    o.apply(ev("SessionStart", 0, meta={"cwd": "/w/tesis"}, origin={"claude_pid": 50, "claude_start": 7}))
    o.apply(ev("SessionStart", 0, sid="s2", meta={"cwd": "/w/other"}))
    procs = [
        proc(50, 1, "claude", start=7, is_claude=True),
        proc(60, 50, "bash"),
        proc(61, 60, "python3"),  # hijo de la sesión -> alta
        proc(70, 1, "topas", cwd="/w/other/run"),  # mismo cwd -> baja
        proc(80, 1, "root", cwd="/elsewhere"),  # sin evidencia
        proc(90, 1, "vim"),  # fuera de la allowlist
    ]
    changed, events = o.process_scan(procs, 1000, ["python3", "topas", "root"], min_age=0)
    py = o.entities["p:61:100"]
    assert py.status == "running" and py.association["confidence"] == "high" and py.parent_id == "s:s1"
    assert o.entities["p:70:100"].association["confidence"] == "low"
    assert o.entities["p:70:100"].parent_id == "s:s2"
    assert o.entities["p:80:100"].association is None
    assert "p:90:100" not in o.entities
    assert {e["event_type"] for e in events} == {"ProcessStart"}
    assert o.entities["s:s1"].process_alive is True
    # El python termina; un PID reutilizado con otra hora de inicio es otra entidad
    _, events = o.process_scan(procs[:2] + [proc(61, 60, "python3", start=999)] + procs[3:], 1010, ["python3", "topas", "root"], min_age=0)
    assert o.entities["p:61:100"].status == "exited"
    assert o.entities["p:61:999"].status == "running"
    assert "ProcessExit" in {e["event_type"] for e in events}


def test_claude_process_gone_marks_session_ended():
    o = Office()
    o.apply(ev("UserPromptSubmit", 0, origin={"claude_pid": 50, "claude_start": 7}))
    o.process_scan([proc(50, 1, "claude", start=7, is_claude=True)], 10, [])
    assert not o.entities["s:s1"].ended
    o.process_scan([], 20, [])
    s = o.entities["s:s1"]
    assert s.ended and s.detail == "process_gone" and s.source == "process_monitor"


def test_counts_claude_without_hooks():
    o = Office()
    o.apply(ev("UserPromptSubmit", 0, origin={"claude_pid": 50}))
    procs = [
        proc(50, 1, "claude", is_claude=True),
        proc(51, 50, "claude", is_claude=True),  # hijo de una sesión conocida (no cuenta)
        proc(52, 1, "claude", is_claude=True),  # sesión sin hooks
        proc(53, 1, "claude", is_claude=True, rc=True),  # servidor remote-control
        proc(54, 53, "claude", is_claude=True),  # sesión lanzada por RC sin hooks
    ]
    o.process_scan(procs, 10, [])
    assert o.claude_without_hooks == 2


# ------------------------------------------------------------ transcripts
def test_transcripts_discover_sessions_without_hooks_but_never_override_hooks():
    o = Office(Timing(idle_after=900, archive_after=3600))
    o.apply(ev("UserPromptSubmit", 900, sid="hooked"))
    found = [
        {"session_id": "nohook", "cwd_guess": "tesis", "mtime": 990, "subagents": [{"agent_id": "x1", "agent_type": "Explore", "mtime": 995}]},
        {"session_id": "hooked", "cwd_guess": "a", "mtime": 999, "subagents": []},
        {"session_id": "ancient", "cwd_guess": "b", "mtime": -10_000, "subagents": []},
    ]
    o.transcript_scan(found, 1000)
    s = o.entities["s:nohook"]
    assert s.status == "working" and s.source == "transcript" and s.confidence == "low" and not s.has_hooks
    assert o.entities["a:nohook:x1"].agent_type == "Explore"
    assert o.entities["s:hooked"].source == "hook" and o.entities["s:hooked"].status == "working"
    assert "s:ancient" not in o.entities
    o.transcript_scan(found, 1200)
    assert s.status == "unknown"
