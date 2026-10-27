"""Servidor local de Claude Code Office (solo lectura)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import datetime as _dt
import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Config, load_config
from .domain.models import iso, parse_iso
from .domain.state_machine import Office, Timing
from .services import process_monitor, transcript_scanner
from .services.broadcaster import Broadcaster
from .services.demo import DemoGenerator
from .services.event_reader import EventReader
from .storage.database import Database, public_event

VERSION = "0.1.0"
log = logging.getLogger("office")
ENTITY_ID_RE = r"^[A-Za-z0-9_.:\-]{1,200}$"
HOOK_MARKER = "claude_hook.py"


def setup_logging(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger("office")
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    for h in (logging.StreamHandler(), logging.FileHandler(data_dir / "backend.log", encoding="utf-8")):
        h.setFormatter(fmt)
        root.addHandler(h)


def hooks_installed() -> dict:
    path = Path(os.path.expanduser("~/.claude/settings.json"))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"settings_file": str(path), "events": []}
    evs = sorted(
        ev
        for ev, groups in (data.get("hooks") or {}).items()
        if isinstance(groups, list) and HOOK_MARKER in json.dumps(groups)
    )
    return {"settings_file": str(path), "events": evs}


class Runtime:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.started = time.time()
        self.db = Database(cfg.db_path)
        self.office = Office(Timing.from_config(cfg["timing"]), self.db.load_entities())
        self.reader = EventReader(cfg.events_dir, self.db.get_setting("reader_offsets", {}))
        self.broadcaster = Broadcaster()
        self.demo = DemoGenerator() if cfg.demo else None
        self.pending_entities: dict[str, dict] = {}
        self.pending_events: list[dict] = []
        self.errors: list[dict] = []
        self.last_hook_event: float | None = self.db.last_event_ts("hook")
        self.tasks: list[asyncio.Task] = []
        self.last_prune = 0.0

    # ----------------------------------------------------------- pipeline
    def note_error(self, component: str, msg: str) -> None:
        log.warning("%s %s", component, msg)
        self.errors = (self.errors + [{"at": iso(time.time()), "component": component, "message": msg[:200]}])[-20:]

    def _mark(self, entities) -> None:
        for e in entities:
            self.pending_entities[e.id] = e.to_public()
        self.db.save_entities(list(entities))

    def ingest(self, events: list[dict], now: float | None = None) -> int:
        n = 0
        for ev in events:
            if self.db.event_exists(ev["event_id"]):
                continue
            eid, changed = self.office.apply(ev, now)
            ev["entity_id"] = eid
            self.db.insert_event(ev)
            self._mark(changed)
            self.pending_events.append(public_event(ev))
            if ev["source"] == "hook":
                self.last_hook_event = max(self.last_hook_event or 0, ev["ts"])
            n += 1
        self.db.commit()
        return n

    def poll_hooks(self) -> int:
        evs = self.reader.read_new()
        n = self.ingest(evs)
        self.db.set_setting("reader_offsets", self.reader.offsets)
        self.db.commit()
        return n

    def scan_processes(self) -> None:
        pc = self.cfg["processes"]
        procs = process_monitor.scan(bool(pc.get("record_script_name")))
        changed, events = self.office.process_scan(procs, time.time(), list(pc.get("allowlist", [])), float(pc.get("min_age_seconds", 3)))
        for ev in events:
            self.db.insert_event(ev)
            self.pending_events.append(public_event(ev))
        self._mark(changed)
        self.db.commit()

    def scan_transcripts(self) -> None:
        found = transcript_scanner.scan(self.office.timing.archive_after)
        self._mark(self.office.transcript_scan(found, time.time()))
        self.db.commit()

    def tick(self) -> None:
        now = time.time()
        self._mark(self.office.tick(now))
        self.db.commit()
        if now - self.last_prune > 3600:
            self.last_prune = now
            days = int(self.cfg["storage"]["retention_days"])
            self.db.prune(now - days * 86400)
            self.reader.prune_files(days)

    def flush(self) -> None:
        if self.pending_entities:
            self.broadcaster.publish({"type": "entities", "entities": list(self.pending_entities.values())})
            self.pending_entities = {}
        if self.pending_events:
            # Límite por mensaje: si hay una ráfaga, los clientes piden historial por HTTP.
            evs = self.pending_events[-100:]
            self.broadcaster.publish({"type": "events", "events": evs, "truncated": len(self.pending_events) > 100})
            self.pending_events = []

    # -------------------------------------------------------------- loops
    async def _loop(self, name: str, interval: float, fn) -> None:
        while True:
            try:
                await asyncio.to_thread(fn)
            except Exception as e:  # noqa: BLE001
                self.note_error(name, f"{type(e).__name__}: {e}")
            await asyncio.sleep(interval)

    async def _demo_loop(self) -> None:
        while True:
            now = time.time()
            self.ingest(self.demo.step(now), now)
            self._mark(self.demo.processes(self.office, now))
            await asyncio.sleep(self.demo.rng.uniform(0.6, 2.2))

    async def _flush_loop(self) -> None:
        beat = 0.0
        while True:
            self.flush()
            if time.time() - beat > 10:
                beat = time.time()
                self.broadcaster.publish({"type": "heartbeat", "server_time": iso(beat), "health": self.health_brief()})
            await asyncio.sleep(0.3)

    def start(self) -> None:
        t = self.cfg["timing"]
        s = self.cfg["sources"]
        mk = asyncio.create_task
        self.tasks.append(mk(self._flush_loop()))
        self.tasks.append(mk(self._loop("tick", 2, self.tick)))
        if self.demo:
            self.tasks.append(mk(self._demo_loop()))
            return
        if s.get("hooks", True):
            self.tasks.append(mk(self._loop("hooks", 0.5, self.poll_hooks)))
        if s.get("process_monitor", True):
            self.tasks.append(mk(self._loop("process_monitor", max(1.0, float(t["process_scan_seconds"])), self.scan_processes)))
        if s.get("transcripts", True):
            self.tasks.append(mk(self._loop("transcripts", max(2.0, float(t["transcript_scan_seconds"])), self.scan_transcripts)))

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self.db.set_setting("reader_offsets", self.reader.offsets)
        self.db.commit()
        self.db.close()

    # ------------------------------------------------------------- health
    def visible_entities(self) -> list[dict]:
        return [e.to_public() for e in self.office.entities.values() if not e.archived]

    def health_brief(self) -> dict:
        active = [e for e in self.office.entities.values() if not e.archived]
        return {
            "demo": self.cfg.demo,
            "last_hook_event_at": iso(self.last_hook_event),
            "last_process_scan_at": iso(self.office.last_process_scan),
            "active_entities": len(active),
        }

    def health(self) -> dict:
        s = self.cfg["sources"]
        return {
            "status": "ok",
            "version": VERSION,
            "server_time": iso(time.time()),
            "uptime_seconds": int(time.time() - self.started),
            "demo": self.cfg.demo,
            "database": {"ok": self.db.ok(), "events": self.db.event_count(), "file": Path(self.cfg.db_path).name},
            "sources": {
                "hooks": {
                    "enabled": bool(s.get("hooks")) and not self.cfg.demo,
                    "events_dir_exists": self.cfg.events_dir.is_dir(),
                    "last_event_at": iso(self.last_hook_event),
                    "malformed_lines": self.reader.malformed,
                    "installed_for_events": hooks_installed()["events"],
                },
                "process_monitor": {
                    "enabled": bool(s.get("process_monitor")) and not self.cfg.demo,
                    "last_scan_at": iso(self.office.last_process_scan),
                    "claude_processes_without_hooks": self.office.claude_without_hooks,
                },
                "transcripts": {
                    "enabled": bool(s.get("transcripts")) and not self.cfg.demo,
                    "last_scan_at": iso(self.office.last_transcript_scan),
                },
            },
            "active_entities": len([e for e in self.office.entities.values() if not e.archived]),
            "recent_errors": self.errors[-10:] + collector_errors(self.cfg.data_dir),
        }


def collector_errors(data_dir: Path) -> list[dict]:
    p = data_dir / "collector.log"
    try:
        with open(p, "rb") as f:
            f.seek(max(0, p.stat().st_size - 4096))
            lines = f.read().decode("utf-8", "replace").splitlines()[-5:]
    except OSError:
        return []
    return [{"component": "collector", "message": ln[:200]} for ln in lines if ln.strip()]


def _parse_since(since: str | None) -> float | None:
    if since is None:
        return None
    try:
        return float(since)
    except ValueError:
        ts = parse_iso(since)
        if ts is None:
            raise HTTPException(400, "since debe ser ISO-8601 o epoch en segundos")
        return ts


def create_app(cfg: Config | None = None, *, start_background: bool = True) -> FastAPI:
    cfg = cfg or load_config()
    setup_logging(cfg.data_dir)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        rt = Runtime(cfg)
        app.state.rt = rt
        if start_background:
            rt.start()
        log.info("server iniciado demo=%s db=%s", cfg.demo, cfg.db_path)
        yield
        await rt.stop()

    app = FastAPI(title="Claude Code Office", version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if int(request.headers.get("content-length") or 0) > 10_000:
            return JSONResponse({"detail": "petición demasiado grande"}, status_code=413)
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def rt(request: Request) -> Runtime:
        return request.app.state.rt

    @app.get("/api/health")
    def health(request: Request):
        return rt(request).health()

    @app.get("/api/config/public")
    def public_config(request: Request):
        return {**rt(request).cfg.public(), "version": VERSION}

    @app.get("/api/entities")
    def entities(request: Request, include_archived: bool = False, limit: int = Query(200, ge=1, le=500)):
        r = rt(request)
        es = sorted(r.office.entities.values(), key=lambda e: e.last_seen_at or 0, reverse=True)
        es = [e for e in es if include_archived or not e.archived][:limit]
        return {"entities": [e.to_public() for e in es]}

    @app.get("/api/entities/{entity_id}")
    def entity(request: Request, entity_id: str = PathParam(..., pattern=ENTITY_ID_RE)):
        r = rt(request)
        e = r.office.entities.get(entity_id)
        if not e:
            raise HTTPException(404, "entidad no encontrada")
        related = [x.to_public() for x in r.office.entities.values() if x.parent_id == e.id or x.id == e.parent_id]
        return {"entity": e.to_public(), "related": related[:50]}

    @app.get("/api/entities/{entity_id}/events")
    def entity_events(request: Request, entity_id: str = PathParam(..., pattern=ENTITY_ID_RE), limit: int = Query(50, ge=1, le=200)):
        r = rt(request)
        if entity_id not in r.office.entities:
            raise HTTPException(404, "entidad no encontrada")
        return {"events": r.db.events(entity_id=entity_id, limit=limit)}

    @app.get("/api/events")
    def events(
        request: Request,
        since: str | None = Query(None, max_length=40),
        event_type: str | None = Query(None, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$"),
        limit: int = Query(50, ge=1, le=500),
    ):
        return {"events": rt(request).db.events(since=_parse_since(since), event_type=event_type, limit=limit)}

    @app.get("/api/stats")
    def stats(request: Request):
        by_status: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for e in rt(request).office.entities.values():
            if e.archived:
                continue
            by_status[e.status] = by_status.get(e.status, 0) + 1
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        return {"by_status": by_status, "by_kind": by_kind}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        origin = websocket.headers.get("origin")
        host = websocket.headers.get("host")
        if origin and urlsplit(origin).netloc != host:
            # Evita que otra web abierta en el navegador lea el panel (CSWSH).
            await websocket.close(code=1008)
            return
        r: Runtime = websocket.app.state.rt
        q = r.broadcaster.register()
        if q is None:
            await websocket.close(code=1013)
            return
        await websocket.accept()
        try:
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "entities": r.visible_entities(),
                    "events": r.db.events(limit=60),
                    "health": r.health_brief(),
                    "server_time": iso(time.time()),
                }
            )

            async def drain_client():
                # El cliente no envía órdenes: se ignora todo lo que llegue.
                while True:
                    await websocket.receive_text()

            reader = asyncio.create_task(drain_client())
            try:
                while True:
                    get = asyncio.create_task(q.get())
                    done, _ = await asyncio.wait({get, reader}, return_when=asyncio.FIRST_COMPLETED)
                    if reader in done:
                        get.cancel()
                        break
                    msg = get.result()
                    if msg.get("type") == "resync":
                        msg = {"type": "snapshot", "entities": r.visible_entities(), "events": r.db.events(limit=60), "health": r.health_brief(), "server_time": iso(time.time())}
                    await websocket.send_json(msg)
            finally:
                reader.cancel()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            r.broadcaster.unregister(q)

    app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
    return app


def main() -> None:
    p = argparse.ArgumentParser(description="Claude Code Office")
    p.add_argument("--config", default=None)
    p.add_argument("--demo", action="store_true", help="modo DEMO con datos ficticios (base de datos separada)")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    a = p.parse_args()
    over: dict = {}
    if a.demo:
        over["demo"] = {"enabled": True}
    if a.host or a.port:
        over["server"] = {k: v for k, v in (("host", a.host), ("port", a.port)) if v}
    cfg = load_config(a.config, over)
    host = cfg["server"]["host"]
    if host in ("0.0.0.0", "::"):
        print("AVISO: escuchando en TODAS las interfaces. Usa la IP de Tailscale o un firewall (ver README).")
    import uvicorn

    uvicorn.run(create_app(cfg), host=host, port=int(cfg["server"]["port"]), log_level="warning", proxy_headers=False, ws_max_size=65536)


if __name__ == "__main__":
    main()
