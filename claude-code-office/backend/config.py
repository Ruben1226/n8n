"""Carga de config.toml con valores por defecto conservadores."""

from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS: dict = {
    "server": {"host": "127.0.0.1", "port": 8765},
    "office": {"name": "Oficina de investigación", "theme": "warm", "reduce_motion": False},
    "sources": {"hooks": True, "transcripts": True, "process_monitor": True},
    "timing": {
        "process_scan_seconds": 5,
        "transcript_scan_seconds": 10,
        "stale_after_seconds": 300,
        "idle_after_seconds": 900,
        "error_visible_seconds": 8,
        "ended_visible_seconds": 300,
        "archive_after_seconds": 3600,
    },
    "storage": {"data_dir": "", "retention_days": 30},
    "processes": {
        "allowlist": ["python", "python3", "python3.*", "root", "root.exe", "topas", "Geant4*", "g4*"],
        "record_script_name": False,
        "min_age_seconds": 3,
    },
    "demo": {"enabled": False},
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def default_data_dir() -> Path:
    env = os.environ.get("CLAUDE_OFFICE_DATA_DIR")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "claude-office"


@dataclass
class Config:
    raw: dict = field(default_factory=lambda: copy.deepcopy(DEFAULTS))

    def __getitem__(self, key: str) -> dict:
        return self.raw[key]

    @property
    def data_dir(self) -> Path:
        d = self.raw["storage"].get("data_dir")
        return Path(d).expanduser() if d else default_data_dir()

    @property
    def events_dir(self) -> Path:
        return self.data_dir / "events"

    @property
    def demo(self) -> bool:
        return bool(self.raw["demo"]["enabled"])

    @property
    def db_path(self) -> Path:
        # El modo demo usa una base de datos separada: nunca se mezcla con el historial real.
        return self.data_dir / ("demo.db" if self.demo else "office.db")

    def public(self) -> dict:
        return {
            "office_name": str(self.raw["office"]["name"])[:80],
            "theme": self.raw["office"]["theme"],
            "reduce_motion": bool(self.raw["office"]["reduce_motion"]),
            "demo": self.demo,
            "stale_after_seconds": self.raw["timing"]["stale_after_seconds"],
            "sources": dict(self.raw["sources"]),
        }


def load_config(path: str | os.PathLike | None = None, overrides: dict | None = None) -> Config:
    raw = copy.deepcopy(DEFAULTS)
    p = Path(path) if path else Path(os.environ.get("CLAUDE_OFFICE_CONFIG", ROOT / "config.toml"))
    if p.exists():
        with open(p, "rb") as f:
            raw = _merge(raw, tomllib.load(f))
    if overrides:
        raw = _merge(raw, overrides)
    return Config(raw)
