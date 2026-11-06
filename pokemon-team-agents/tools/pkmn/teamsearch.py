"""Búsqueda de equipos de 6 con algoritmo genético + función objetivo transparente.

La función objetivo devuelve también el DESGLOSE de cada componente, para que los agentes
(arquitecto y crítico) puedan razonar sobre por qué un equipo puntúa como puntúa.
Pesos configurables en config/pesos_equipo.json.
"""
from __future__ import annotations

import json
import os
import random
from collections import Counter

from .data import ROOT, key
from .typechart import TYPES, effectiveness

DEFAULT_WEIGHTS = {
    "defensa_tipos": 0.8, "amenazas": 2.0, "presion_ofensiva": 1.5, "roles": 0.8, "velocidad": 0.8,
    "calidad_individual": 1.2, "penal_debilidad_compartida": 1.0, "penal_eslabon_debil": 2.0,
    "percentil_eslabon": 0.4, "penal_menta": 50.0, "penal_objeto": 50.0, "penal_especie": 100.0,
    "roles_deseados": {"hazard_set": 1.0, "hazard_remove": 0.8, "pivot": 0.8, "speed_control": 1.0,
                        "setup_wincon": 1.0, "recovery": 0.6, "status_spreader": 0.5, "priority": 0.5},
}


def load_weights() -> dict:
    p = os.path.join(ROOT, "config", "pesos_equipo.json")
    w = dict(DEFAULT_WEIGHTS)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            w.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})
    return w


def _def_mult(s: dict, atk_type: str) -> float:
    for e in s.get("ability_effects", []):
        if e["kind"] == "immunity" and e["type"] == atk_type:
            return 0.0
    m = effectiveness(atk_type, s["types"])
    for e in s.get("ability_effects", []):
        if e["kind"] == "incoming_type_mult" and e["type"] == atk_type:
            m *= e["mult"]
        if e["kind"] == "incoming_se_mult" and m > 1:
            m *= e["mult"]
    return m


def evaluate(team: list[dict], matrix: dict, threats: list[dict], rules: dict, w: dict,
             quality_floor: float | None = None) -> dict:
    """Puntúa un equipo. Filosofía: NO existe el equipo perfecto. Se premia lo que gana partidas
    (responder a amenazas y golpear fuerte) y la cobertura de tipos tiene rendimiento decreciente;
    meter a un Pokémon flojo solo para tapar un tipo se penaliza (eslabón débil)."""
    br = {}
    ids = [s["id"] for s in team]

    def mx(sid, tid):
        return matrix.get(sid, {}).get(tid, {})

    # 1. Defensa por tipos (rendimiento decreciente)
    dscore, shared = 0.0, []
    for t in TYPES:
        mults = [_def_mult(s, t) for s in team]
        weak = sum(1 for m in mults if m > 1)
        resist = sum(1 for m in mults if m < 1)
        immune = sum(1 for m in mults if m == 0)
        dscore += min(resist, 2) * 0.5 + min(immune, 1) * 0.5 - max(0, weak - 1) * 0.5 - (0.1 if weak else 0)
        if weak >= 3 or (weak >= 2 and resist == 0):
            shared.append(t)
    br["defensa_tipos"] = round(dscore / len(TYPES) * 3, 3)

    # 2. Respuestas a amenazas (check/counter)
    tscore, sin_respuesta = 0.0, []
    for th in threats:
        checks = sum(1 for i in ids if mx(i, th["id"]).get("check"))
        counters = sum(1 for i in ids if mx(i, th["id"]).get("counter"))
        tscore += (min(checks, 2) * 0.5 + min(counters, 1) * 0.5) * th.get("weight", 1.0)
        if checks == 0:
            sin_respuesta.append(th["id"])
    total_w = sum(th.get("weight", 1.0) for th in threats) or 1
    br["amenazas"] = round(tscore / total_w * 3, 3)
    br["amenazas_sin_respuesta"] = sin_respuesta

    # 3. Presión ofensiva: ¿cuánto daño real metemos a cada amenaza? (premia los "botones" enormes)
    pscore = 0.0
    for th in threats:
        best = max((min(100.0, mx(i, th["id"]).get("c2t", {}).get("min_pct", 0.0)) for i in ids), default=0.0)
        ohko = any(mx(i, th["id"]).get("c2t", {}).get("hits_to_ko", [99, 99])[1] <= 1 for i in ids)
        pscore += (best / 100 + (0.3 if ohko else 0)) * th.get("weight", 1.0)
    br["presion_ofensiva"] = round(pscore / total_w * 2.3, 3)

    # Debilidades compartidas: penalización BLANDA, que se perdona si el equipo responde de verdad
    # a los atacantes de ese tipo (dos checks a los atacantes genéricos físico y especial del tipo).
    pen_shared, perdonadas = 0.0, []
    for t in shared:
        gen = [f"GEN-atacante-{t}-physical", f"GEN-atacante-{t}-special"]
        handled = all(sum(1 for i in ids if mx(i, g).get("check")) >= 2 for g in gen if any(th["id"] == g for th in threats))
        if handled:
            perdonadas.append(t)
            pen_shared += 0.25
        else:
            pen_shared += 1.0
    br["debilidades_compartidas"] = shared
    br["debilidades_compartidas_compensadas"] = perdonadas

    # 4. Roles
    tags = Counter(t for s in team for t in s.get("role_tags", []))
    br["roles"] = round(sum(v for r, v in w["roles_deseados"].items() if tags.get(r)), 3)
    br["roles_faltantes"] = [r for r in w["roles_deseados"] if not tags.get(r)]

    # 5. Velocidad
    fast = sum(1 for s in team if "fast" in s.get("role_tags", []) or "speed_control" in s.get("role_tags", []))
    br["velocidad"] = round(min(fast, 3) / 3 * 2, 3)

    # 6. Calidad individual
    # percentil dentro del rol: compara atacantes con atacantes y soportes con soportes
    br["calidad_individual"] = round(sum(_q(s) for s in team) / len(team) * 6, 3)

    # Penalizaciones
    pen = pen_shared * w["penal_debilidad_compartida"]
    eslabones = []
    if quality_floor:
        for s in team:
            if _q(s) < quality_floor:
                eslabones.append(s["id"])
                pen += w["penal_eslabon_debil"] * (quality_floor - _q(s)) / quality_floor
    br["eslabones_debiles"] = eslabones
    species = Counter(s["species"] for s in team)
    if rules.get("clausula_especie", True):
        pen += sum(c - 1 for c in species.values()) * w["penal_especie"]
    mints = sum(1 for s in team if s.get("needs_mint"))
    pen += max(0, mints - rules.get("mentas_disponibles", 0)) * w["penal_menta"]
    items = Counter(key(s["item"]) for s in team if s.get("item"))
    stock = rules.get("_stock_objetos", {})
    for it, c in items.items():
        limit = stock.get(it, 1 if rules.get("clausula_objeto", False) else 99)
        pen += max(0, c - limit) * w["penal_objeto"]
    br["penalizacion"] = round(pen, 3)
    br["mentas_usadas"] = mints
    comps = ("defensa_tipos", "amenazas", "presion_ofensiva", "roles", "velocidad", "calidad_individual")
    br["total"] = round(sum(br[k] * w[k] for k in comps) - pen, 3)
    return br


def _q(s: dict) -> float:
    return s["scores"].get("percentil_rol", 0.5)


def quality_floor_of(candidates: list[dict], w: dict) -> float:
    """Umbral de 'eslabón débil' en percentil dentro del rol (por defecto 0.4)."""
    return w.get("percentil_eslabon", 0.4)


def search(candidates: list[dict], matrix: dict, threats: list[dict], rules: dict, w: dict | None = None,
           pop: int = 200, gens: int = 150, seed: int = 7, top_n: int = 10, locked: list[str] | None = None) -> list[dict]:
    w = w or load_weights()
    rng = random.Random(seed)
    by_species: dict[str, list[dict]] = {}
    for c in candidates:
        by_species.setdefault(c["species"], []).append(c)
    species = list(by_species)
    locked = locked or []
    if len(species) < 6:
        raise ValueError("Hacen falta al menos 6 especies distintas")

    def random_team():
        chosen = list(locked) + rng.sample([s for s in species if s not in locked], 6 - len(locked))
        return [rng.choice(by_species[s]) for s in chosen]

    qf = quality_floor_of(candidates, w)

    def fit(team):
        return evaluate(team, matrix, threats, rules, w, qf)["total"]

    def mutate(team):
        t = list(team)
        i = rng.randrange(6)
        if t[i]["species"] in locked or rng.random() < 0.5:
            t[i] = rng.choice(by_species[t[i]["species"]])  # otro set del mismo Pokémon
        else:
            used = {s["species"] for s in t}
            new = rng.choice([s for s in species if s not in used] or species)
            t[i] = rng.choice(by_species[new])
        return t

    def crossover(a, b):
        pool = {s["species"]: s for s in a + b}
        sp = list(pool)
        rng.shuffle(sp)
        keep = [x for x in sp if x in locked]
        rest = [x for x in sp if x not in locked]
        return [pool[x] for x in (keep + rest)[:6]]

    population = [random_team() for _ in range(pop)]
    cache: dict[tuple, float] = {}

    def f(team):
        k = tuple(sorted(s["id"] for s in team))
        if k not in cache:
            cache[k] = fit(team)
        return cache[k]

    for _ in range(gens):
        population.sort(key=f, reverse=True)
        elite = population[: pop // 5]
        children = list(elite)
        while len(children) < pop:
            a, b = rng.sample(elite, 2)
            child = crossover(a, b) if rng.random() < 0.6 else list(a)
            if rng.random() < 0.8:
                child = mutate(child)
            if len(child) == 6:
                children.append(child)
        population = children

    population.sort(key=f, reverse=True)
    results, seen = [], set()
    for team in sorted({tuple(sorted(s["id"] for s in t)): t for t in population}.values(), key=f, reverse=True):
        k = tuple(sorted(s["species"] for s in team))  # un resultado por composición de especies
        if k in seen:
            continue
        seen.add(k)
        results.append({"team": [s["id"] for s in team], "sets": team,
                        "breakdown": evaluate(team, matrix, threats, rules, w, qf)})
        if len(results) >= top_n:
            break
    return results


def to_showdown(s: dict) -> str:
    nat_es = s["nature"]
    lines = [f"{s['species']}" + (f" @ {s['item']}" if s.get("item") else ""),
             f"Ability: {s['ability']}", f"Level: {s.get('level', 49)}", f"{nat_es} Nature"]
    ivs = s.get("ivs") or {}
    low = [f"{v} {k.upper()}" for k, v in ivs.items() if v != 31]
    if low:
        lines.append("IVs: " + " / ".join(low))
    lines += [f"- {m}" for m in s["moves"]]
    return "\n".join(lines)
