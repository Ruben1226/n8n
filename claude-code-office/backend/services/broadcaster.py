"""Difusión de deltas a clientes WebSocket con colas acotadas."""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("office.ws")
MAX_CLIENTS = 32
QUEUE_SIZE = 200


class Broadcaster:
    def __init__(self):
        self.clients: set[asyncio.Queue] = set()

    def register(self) -> asyncio.Queue | None:
        if len(self.clients) >= MAX_CLIENTS:
            return None
        q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self.clients.add(q)
        return q

    def unregister(self, q: asyncio.Queue) -> None:
        self.clients.discard(q)

    def publish(self, msg: dict) -> None:
        for q in list(self.clients):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                # Cliente lento: se vacía su cola y se le pide un resync completo.
                while not q.empty():
                    q.get_nowait()
                q.put_nowait({"type": "resync"})
