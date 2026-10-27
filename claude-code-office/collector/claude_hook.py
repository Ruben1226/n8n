#!/usr/bin/env python3
"""Hook de Claude Code para Claude Code Office.

Lee el JSON del evento desde stdin, conserva solo metadatos (nunca prompts,
respuestas, tool_input ni tool_response) y añade una línea a un JSONL local.

Diseño:
- Solo biblioteca estándar: se ejecuta con cualquier python3 del sistema.
- No hace peticiones de red ni espera al servidor web.
- Siempre termina con código 0 y sin escribir en stdout, para no alterar
  nunca el comportamiento de Claude Code.
"""

from __future__ import annotations

import datetime as _dt
import fcntl
import json
import os
import sys
import uuid

SCHEMA_VERSION = 1
MAX_STDIN_BYTES = 32_000_000
MAX_STR = 200

# Campos escalares del payload real de Claude Code que se conservan tal cual
# (recortados). Todo lo demás se descarta.
KEEP_TOP = ("session_id", "agent_id", "agent_type", "tool_name", "tool_use_id", "prompt_id")
KEEP_META = (
    "source",  # SessionStart: startup | resume | clear | compact
    "reason",  # SessionEnd
    "notification_type",  # Notification
    "permission_mode",
    "duration_ms",
    "is_interrupt",  # PostToolUseFailure
    "stop_hook_active",
    "trigger",  # PreCompact: manual | auto
    "model",
    "cwd",
)


def data_dir() -> str:
    d = os.environ.get("CLAUDE_OFFICE_DATA_DIR")
    if not d:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        d = os.path.join(base, "claude-office")
    return d


def _clip(v):
    if isinstance(v, str):
        return v[:MAX_STR]
    if isinstance(v, (bool, int, float)) or v is None:
        return v
    return None


def _read_proc(pid: int, name: str) -> bytes | None:
    try:
        with open(f"/proc/{pid}/{name}", "rb") as f:
            return f.read(65536)
    except OSError:
        return None


def _stat_fields(pid: int) -> tuple[int, int] | None:
    """Devuelve (ppid, starttime_ticks) leyendo /proc/<pid>/stat."""
    raw = _read_proc(pid, "stat")
    if not raw:
        return None
    try:
        rest = raw[raw.rindex(b")") + 2 :].split()
        return int(rest[1]), int(rest[19])
    except (ValueError, IndexError):
        return None


def _is_claude(argv: list[str], comm: str) -> bool:
    if comm in ("claude", "claude.exe"):
        return True
    names = [os.path.basename(a) for a in argv[:3]]
    if any(n in ("claude", "claude.exe") for n in names):
        return True
    # Instalación npm: node .../@anthropic-ai/claude-code/cli.js
    return any("claude-code" in a and a.endswith(("cli.js", "cli.mjs")) for a in argv[:3])


def _is_remote_control(argv: list[str]) -> bool:
    return any(a == "remote-control" or a == "--remote-control" or a.startswith("--remote-control=") for a in argv[1:8])


def detect_origin() -> dict:
    """Metadatos sobre cómo se lanzó la sesión. No guarda argumentos: solo
    banderas booleanas y el PID/hora de inicio del proceso claude."""
    env = os.environ
    origin: dict = {
        "entrypoint": _clip(env.get("CLAUDE_CODE_ENTRYPOINT")),
        "cloud": env.get("CLAUDE_CODE_REMOTE") == "true",
        "tmux": bool(env.get("TMUX")),
        "remote_control": False,
        "claude_pid": None,
        "claude_start": None,
    }
    if not sys.platform.startswith("linux"):
        return origin
    pid = os.getppid()
    for _ in range(10):
        if pid <= 1:
            break
        argv = [a.decode("utf-8", "replace") for a in (_read_proc(pid, "cmdline") or b"").split(b"\0") if a]
        comm = (_read_proc(pid, "comm") or b"").decode("utf-8", "replace").strip()
        st = _stat_fields(pid)
        if origin["claude_pid"] is None and _is_claude(argv, comm):
            origin["claude_pid"] = pid
            origin["claude_start"] = st[1] if st else None
        if _is_claude(argv, comm) and _is_remote_control(argv):
            origin["remote_control"] = True
        if not st:
            break
        pid = st[0]
    return origin


def normalize(payload: dict, origin: dict, now: _dt.datetime | None = None) -> dict | None:
    event_type = payload.get("hook_event_name")
    if not isinstance(event_type, str) or not event_type:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    ev: dict = {
        "v": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "timestamp": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "event_type": event_type[:64],
        "source": "hook",
    }
    for k in KEEP_TOP:
        v = _clip(payload.get(k))
        if isinstance(v, str) and v:
            ev[k] = v
    meta = {}
    for k in KEEP_META:
        if k in payload:
            v = _clip(payload[k])
            if v is not None:
                meta[k] = v
    effort = payload.get("effort")
    if isinstance(effort, dict) and isinstance(effort.get("level"), str):
        meta["effort"] = effort["level"][:20]
    tasks = payload.get("background_tasks")
    if isinstance(tasks, list):
        meta["background_running"] = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "running")
    if event_type == "PostToolUseFailure":
        meta["is_error"] = True
    ev["meta"] = meta
    ev["origin"] = origin
    return ev


def append_event(ev: dict, directory: str) -> str:
    os.makedirs(directory, mode=0o700, exist_ok=True)
    day = ev["timestamp"][:10]
    path = os.path.join(directory, f"hooks-{day}.jsonl")
    line = (json.dumps(ev, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    return path


def _log_error(msg: str) -> None:
    try:
        d = data_dir()
        os.makedirs(d, mode=0o700, exist_ok=True)
        with open(os.path.join(d, "collector.log"), "a", encoding="utf-8") as f:
            ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
            f.write(f"{ts} ERROR collector {msg[:300]}\n")
    except OSError:
        pass


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        if len(raw) > MAX_STDIN_BYTES:
            # Payload enorme (p. ej. tool_response gigante): solo nos interesa
            # la cabecera, pero no se puede parsear parcialmente; se descarta.
            _log_error("payload demasiado grande; evento descartado")
            return 0
        payload = json.loads(raw.decode("utf-8", "replace") or "null")
        if not isinstance(payload, dict):
            _log_error("payload no es un objeto JSON")
            return 0
        ev = normalize(payload, detect_origin())
        if ev is None:
            _log_error("payload sin hook_event_name")
            return 0
        append_event(ev, os.path.join(data_dir(), "events"))
    except Exception as e:  # noqa: BLE001 - un hook nunca debe fallar
        _log_error(f"{type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
