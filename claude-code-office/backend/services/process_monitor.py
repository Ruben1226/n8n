"""Escaneo de procesos vía /proc, sin privilegios y sin dependencias.

Solo se leen: comm, stat (ppid, hora de inicio), enlace exe, enlace cwd y,
únicamente para detectar si es Claude Code, la línea de comandos. Nunca se
guardan argumentos ni variables de entorno.
"""

from __future__ import annotations

import os
import sys

from ..domain.state_machine import ProcInfo

INTERPRETERS = ("python", "python3", "pypy", "pypy3")


def _read(path: str, n: int = 65536) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return None


def _boot_time() -> float:
    raw = _read("/proc/stat") or b""
    for line in raw.splitlines():
        if line.startswith(b"btime "):
            return float(line.split()[1])
    return 0.0


def _is_claude(comm: str, argv: list[str]) -> bool:
    if comm in ("claude", "claude.exe"):
        return True
    if any(os.path.basename(a) in ("claude", "claude.exe") for a in argv[:2]):
        return True
    return any("claude-code" in a and a.endswith(("cli.js", "cli.mjs")) for a in argv[:3])


def _script_name(argv: list[str]) -> str | None:
    for a in argv[1:6]:
        if a.startswith("-"):
            if a in ("-m", "-c"):
                return None
            continue
        return os.path.basename(a)[:80] or None
    return None


def scan(record_script_name: bool = False) -> list[ProcInfo]:
    if not sys.platform.startswith("linux") or not os.path.isdir("/proc"):
        return []
    uid = os.getuid()
    ticks = os.sysconf("SC_CLK_TCK")
    boot = _boot_time()
    out: list[ProcInfo] = []
    me = os.getpid()
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == me:
            continue  # el propio backend no es trabajo del usuario
        base = f"/proc/{pid}"
        try:
            if os.stat(base).st_uid != uid:
                continue
        except OSError:
            continue
        raw = _read(f"{base}/stat")
        if not raw:
            continue
        try:
            comm = raw[raw.index(b"(") + 1 : raw.rindex(b")")].decode("utf-8", "replace")
            rest = raw[raw.rindex(b")") + 2 :].split()
            ppid, start_ticks = int(rest[1]), int(rest[19])
        except (ValueError, IndexError):
            continue
        argv = [a.decode("utf-8", "replace") for a in (_read(f"{base}/cmdline") or b"").split(b"\0") if a]
        try:
            exe_name = os.path.basename(os.readlink(f"{base}/exe"))
        except OSError:
            exe_name = None
        try:
            cwd = os.readlink(f"{base}/cwd")
        except OSError:
            cwd = None
        is_claude = _is_claude(comm, argv)
        out.append(
            ProcInfo(
                pid=pid,
                ppid=ppid,
                start_ticks=start_ticks,
                start_epoch=boot + start_ticks / ticks,
                comm=comm,
                exe_name=exe_name,
                cwd=cwd,
                script_name=_script_name(argv) if record_script_name and comm.startswith(INTERPRETERS) else None,
                is_claude=is_claude,
                rc_server=is_claude and len(argv) > 1 and "remote-control" in argv[1:3],
            )
        )
    return out
