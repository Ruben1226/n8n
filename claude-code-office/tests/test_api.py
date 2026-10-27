import time

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import load_config
from collector import claude_hook
from conftest import hook_records


def make_client(tmp_path, **over):
    cfg = load_config(tmp_path / "missing.toml", {"storage": {"data_dir": str(tmp_path / "data")}, **over})
    return TestClient(create_app(cfg, start_background=False)), cfg


def recent_records():
    return hook_records(t0=time.time() - 100)


def write_hooks(cfg, records):
    for r in records:
        claude_hook.append_event(r, str(cfg.events_dir))


@pytest.fixture
def client(tmp_path):
    c, cfg = make_client(tmp_path)
    with c:
        c.cfg = cfg
        yield c


def test_health_and_empty_state(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["database"]["ok"] and h["demo"] is False
    assert client.get("/api/entities").json() == {"entities": []}
    assert client.get("/api/events").json() == {"events": []}
    assert client.get("/api/stats").json() == {"by_status": {}, "by_kind": {}}
    pub = client.get("/api/config/public").json()
    assert set(pub) >= {"office_name", "demo", "stale_after_seconds"}


def test_hook_events_flow_into_entities(client):
    write_hooks(client.cfg, recent_records())
    with open(client.cfg.events_dir / "hooks-2026-01-15.jsonl", "a") as f:
        f.write("garbage line\n{\"event_type\": \"Stop\"}\n")
    rt = client.app.state.rt
    n = rt.poll_hooks()
    assert n == 16
    assert rt.reader.malformed == 2
    ents = {e["id"]: e for e in client.get("/api/entities").json()["entities"]}
    sid = "65f5ab18-145f-5123-8d1f-9d422d3b358e"
    assert ents[f"s:{sid}"]["status"] == "completed"
    assert ents[f"a:{sid}:a0d5980ec0cf098e7"]["parent_id"] == f"s:{sid}"
    detail = client.get(f"/api/entities/s:{sid}").json()
    assert detail["related"][0]["kind"] == "subagent"
    evs = client.get(f"/api/entities/s:{sid}/events?limit=5").json()["events"]
    assert len(evs) == 5 and evs[0]["event_type"] == "SessionEnd"
    # Re-leer no duplica
    rt.reader.offsets = {}
    assert rt.poll_hooks() == 0
    assert client.get("/api/health").json()["database"]["events"] == 16
    stats = client.get("/api/stats").json()
    assert stats["by_kind"] == {"claude_session": 1, "subagent": 1}


def test_history_survives_restart(tmp_path):
    c, cfg = make_client(tmp_path)
    with c:
        write_hooks(cfg, recent_records())
        c.app.state.rt.poll_hooks()
    c2, _ = make_client(tmp_path)
    with c2:
        assert c2.get("/api/health").json()["database"]["events"] == 16
        assert len(c2.get("/api/entities").json()["entities"]) == 2
        assert c2.app.state.rt.poll_hooks() == 0  # offsets persistidos


def test_pagination_limits_and_validation(client):
    assert client.get("/api/events?limit=501").status_code == 422
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/entities/x/events?limit=1000").status_code == 422
    assert client.get("/api/events?since=yesterday").status_code == 400
    assert client.get("/api/events?since=2026-01-01T00:00:00Z").status_code == 200
    assert client.get("/api/events?event_type=Stop;DROP").status_code == 422
    assert client.get("/api/entities/" + "a" * 300).status_code == 422
    assert client.get("/api/entities/nope").status_code == 404


def test_no_arbitrary_files_or_commands(client):
    for path in ("/../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fetc%2fpasswd", "/api/../config.example.toml", "/backend/app.py"):
        r = client.get(path)
        assert "root:" not in r.text and "def create_app" not in r.text and "[server]" not in r.text, path
    for method in ("post", "put", "delete", "patch"):
        assert getattr(client, method)("/api/entities").status_code == 405
    assert client.get("/api/exec").status_code == 404
    r = client.get("/")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]


def test_websocket_snapshot_and_origin_check(client):
    write_hooks(client.cfg, recent_records())
    client.app.state.rt.poll_hooks()
    with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "snapshot" and len(msg["entities"]) == 2 and msg["events"]
    with pytest.raises(Exception):
        with client.websocket_connect("/ws", headers={"origin": "http://evil.example"}) as ws:
            ws.receive_json()


def test_demo_uses_separate_database(tmp_path):
    c, cfg = make_client(tmp_path, demo={"enabled": True})
    assert cfg.db_path.name == "demo.db"
    with c:
        rt = c.app.state.rt
        now = time.time()
        rt.ingest(rt.demo.step(now), now)
        rt._mark(rt.demo.processes(rt.office, now))
        ents = c.get("/api/entities").json()["entities"]
        assert ents and all(e["source"] == "demo" for e in ents)
        assert c.get("/api/health").json()["demo"] is True
    assert not (tmp_path / "data" / "office.db").exists()
