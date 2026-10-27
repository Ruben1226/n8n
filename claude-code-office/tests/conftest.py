import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collector import claude_hook  # noqa: E402
from backend.domain.event_normalizer import normalize_record  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "hook_payloads_cc2.1.311.jsonl"
ORIGIN = {"entrypoint": "cli", "cloud": False, "tmux": True, "remote_control": True, "claude_pid": None, "claude_start": None}


def load_payloads() -> list[dict]:
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


def hook_records(origin=None, t0=1_800_000_000.0, step=1.0) -> list[dict]:
    """Payloads reales -> registros JSONL tal como los escribe el hook, con
    timestamps deterministas."""
    import datetime as dt

    out = []
    for i, p in enumerate(load_payloads()):
        now = dt.datetime.fromtimestamp(t0 + i * step, dt.timezone.utc)
        out.append(claude_hook.normalize(p, origin or ORIGIN, now))
    return out


def hook_events(**kw) -> list[dict]:
    return [normalize_record(r, now=2_000_000_000.0) for r in hook_records(**kw)]


@pytest.fixture
def payloads():
    return load_payloads()
