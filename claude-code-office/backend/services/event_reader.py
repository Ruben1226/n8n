"""Lectura incremental de los JSONL que escribe el hook.

Guarda un offset por archivo (con su inodo) para no releer ni perder
eventos tras un reinicio del backend. Solo consume líneas completas.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
import re
import time
from pathlib import Path

from ..domain.event_normalizer import MAX_LINE_BYTES, normalize_line

log = logging.getLogger("office.reader")
FILE_RE = re.compile(r"^hooks-(\d{4}-\d{2}-\d{2})\.jsonl$")
MAX_BYTES_PER_PASS = 4_000_000


class EventReader:
    def __init__(self, directory: Path, offsets: dict | None = None):
        self.dir = Path(directory)
        self.offsets: dict[str, dict] = dict(offsets or {})
        self.malformed = 0
        self.last_file_mtime: float | None = None
        self.last_error: str | None = None

    def read_new(self, now: float | None = None) -> list[dict]:
        out: list[dict] = []
        if not self.dir.is_dir():
            return out
        budget = MAX_BYTES_PER_PASS
        names = sorted(n for n in os.listdir(self.dir) if FILE_RE.match(n))
        for name in names:
            if budget <= 0:
                break
            path = self.dir / name
            try:
                st = path.stat()
            except OSError:
                continue
            self.last_file_mtime = max(self.last_file_mtime or 0, st.st_mtime)
            info = self.offsets.get(name)
            if not info or info.get("inode") != st.st_ino or info.get("offset", 0) > st.st_size:
                info = {"inode": st.st_ino, "offset": 0}
            if info["offset"] >= st.st_size:
                self.offsets[name] = info
                continue
            try:
                with open(path, "rb") as f:
                    f.seek(info["offset"])
                    chunk = f.read(min(budget, st.st_size - info["offset"]))
            except OSError as e:
                self.last_error = f"{name}: {e.strerror}"
                continue
            end = chunk.rfind(b"\n")
            if end < 0:
                if len(chunk) > MAX_LINE_BYTES:
                    # Línea gigante sin salto: se salta para no bloquear la lectura.
                    info["offset"] += len(chunk)
                    self.malformed += 1
                self.offsets[name] = info
                continue
            for line in chunk[: end + 1].split(b"\n"):
                if not line.strip():
                    continue
                ev = normalize_line(line, now)
                if ev is None:
                    self.malformed += 1
                    continue
                out.append(ev)
            info["offset"] += end + 1
            budget -= end + 1
            self.offsets[name] = info
        return out

    def prune_files(self, retention_days: int, today: _dt.date | None = None) -> list[str]:
        today = today or _dt.date.today()
        removed = []
        if not self.dir.is_dir():
            return removed
        for name in os.listdir(self.dir):
            m = FILE_RE.match(name)
            if not m:
                continue
            try:
                day = _dt.date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if (today - day).days > retention_days:
                try:
                    os.remove(self.dir / name)
                    self.offsets.pop(name, None)
                    removed.append(name)
                except OSError:
                    pass
        return removed

    def last_line_age(self) -> float | None:
        return None if self.last_file_mtime is None else time.time() - self.last_file_mtime
