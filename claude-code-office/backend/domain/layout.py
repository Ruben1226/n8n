"""Asignación estable de puestos por zona (la geometría vive en el frontend)."""

from __future__ import annotations

import re

ZONES = {"coordination": 6, "agents": 12, "review": 6, "lab": 8}
REVIEW_RE = re.compile(r"review|verif|audit|test|check|critic", re.I)


def zone_for(kind: str, agent_type: str | None = None) -> str:
    if kind == "claude_session":
        return "coordination"
    if kind == "external_process":
        return "lab"
    if kind == "subagent" and agent_type and REVIEW_RE.search(agent_type):
        return "review"
    return "agents"


def assign_desk(entities, entity) -> dict:
    """Primer puesto libre de la zona entre las entidades no archivadas.
    Si la zona está llena se devuelven índices >= capacidad (el frontend
    los coloca en filas de desbordamiento)."""
    zone = zone_for(entity.kind, entity.agent_type)
    used = {
        e.desk["slot"]
        for e in entities
        if e is not entity and not e.archived and e.desk and e.desk.get("zone") == zone
    }
    slot = 0
    while slot in used:
        slot += 1
    return {"zone": zone, "slot": slot}
