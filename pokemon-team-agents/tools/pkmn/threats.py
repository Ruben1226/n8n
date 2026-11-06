"""Amenazas sin meta: (a) los mejores sets del propio pool (el pool de tus colegas sale del mismo
randomizer, así que su distribución es parecida) y (b) arquetipos genéricos por tipo.
También construye la matriz de enfrentamientos candidato × amenaza."""
from __future__ import annotations

from .damage import Battler, battler_from_set, calc, effective_speed
from .typechart import TYPES

GENERIC_ATTACKER = {"hp": 85, "atk": 110, "def": 80, "spa": 110, "spd": 80, "spe": 100}
GENERIC_WALL = {"hp": 100, "atk": 70, "def": 115, "spa": 70, "spd": 115, "spe": 50}


def _generic_move(t: str, cat: str, bp: int = 90) -> dict:
    return {"name": f"STAB-{t}-{cat}", "type": t, "category": cat, "power": bp, "accuracy": 100, "tags": []}


def generic_threats() -> list[dict]:
    out = []
    for t in TYPES:
        for cat in ("physical", "special"):
            out.append({
                "id": f"GEN-atacante-{t}-{cat}", "species": f"Atacante genérico {t} ({cat})", "types": [t],
                "base_stats": GENERIC_ATTACKER, "ability": None, "ability_effects": [], "item": None,
                "item_effects": [], "nature": "Adamant" if cat == "physical" else "Modest",
                "move_data": [_generic_move(t, cat)], "moves": [f"STAB-{t}-{cat}"], "generic": True,
                "weight": 0.6,
            })
        out.append({
            "id": f"GEN-muro-{t}", "species": f"Muro genérico {t}", "types": [t], "base_stats": GENERIC_WALL,
            "ability": None, "ability_effects": [], "item": "Leftovers", "item_effects": [], "nature": "Bold",
            "move_data": [_generic_move(t, "physical", 70)], "moves": [f"STAB-{t}-physical"], "generic": True,
            "weight": 0.4,
        })
    return out


def pool_threats(sets: list[dict], n: int = 30) -> list[dict]:
    seen, out = set(), []
    for s in sorted(sets, key=lambda s: s["scores"]["total"], reverse=True):
        if s["species"] in seen or s["role"] == "soporte":
            continue
        seen.add(s["species"])
        out.append({**s, "weight": 1.0, "threat_source": "pool"})
        if len(out) >= n:
            break
    return out


def _moves_of(dex, s: dict) -> list[dict]:
    if s.get("move_data"):
        return s["move_data"]
    return [m for m in (dex.move(x) for x in s["moves"]) if m]


def _best(att: Battler, dfn: Battler, moves: list[dict]) -> dict:
    best = {"move": None, "min_pct": 0.0, "max_pct": 0.0, "hits_to_ko": (99, 99), "priority": False}
    for md in moves:
        if md.get("category") == "status":
            continue
        r = calc(att, dfn, md)
        acc = (md.get("accuracy") or 100) / 100
        if (r["min_pct"] + r["max_pct"]) * acc > (best["min_pct"] + best["max_pct"]) * best.get("acc", 1):
            best = {"move": md["name"], "min_pct": r["min_pct"], "max_pct": r["max_pct"],
                    "hits_to_ko": list(r["hits_to_ko"]), "priority": md.get("priority", 0) > 0, "acc": acc}
    return best


def matchup(dex, c: dict, t: dict) -> dict:
    a = battler_from_set(dex, c)
    b = battler_from_set(dex, t)
    c2t = _best(a, b, _moves_of(dex, c))
    t2c = _best(b, a, _moves_of(dex, t))
    sa, sb = effective_speed(a), effective_speed(b)
    faster = 1.0 if sa > sb else 0.5 if sa == sb else 0.0
    c_hits = c2t["hits_to_ko"][1]  # peor tirada propia
    t_hits = t2c["hits_to_ko"][0]  # mejor tirada rival
    wins_1v1 = (c_hits < t_hits) or (c_hits == t_hits and faster == 1.0) or (c2t["priority"] and c2t["hits_to_ko"][1] == 1)
    # counter: entra recibiendo un golpe y aun así gana
    t_hits_after_switch = t_hits - 1
    counter = wins_1v1 and t2c["max_pct"] < 50 and (c_hits < t_hits_after_switch or (c_hits == t_hits_after_switch and faster == 1.0))
    return {"c2t": c2t, "t2c": t2c, "speed": [sa, sb], "faster": faster,
            "check": bool(wins_1v1), "counter": bool(counter)}


def build_matrix(dex, candidates: list[dict], threats: list[dict]) -> dict:
    m = {}
    for c in candidates:
        row = {}
        for t in threats:
            if t.get("species") == c["species"]:
                continue
            row[t["id"]] = matchup(dex, c, t)
        m[c["id"]] = row
    return m
