"""Calculadora de daño (fórmula Gen 5+) con efectos genéricos de habilidades y objetos.

Los efectos vienen como lista de dicts con un vocabulario fijo (ver knowledge/12-vocabulario-efectos.md).
Precisión: ±1-2 puntos frente a Showdown por redondeos simplificados; suficiente para decidir.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .stats import apply_stage, calc_all
from .typechart import effectiveness, norm_type


@dataclass
class Battler:
    name: str
    types: list[str]
    base_stats: dict
    ability: str | None = None
    item: str | None = None
    nature: str = "Serious"
    level: int = 49
    ivs: dict = field(default_factory=dict)
    evs: dict = field(default_factory=dict)
    moves: list[str] = field(default_factory=list)
    stages: dict = field(default_factory=dict)
    status: str | None = None          # brn, par, psn, tox, slp, frz
    hp_frac: float = 1.0
    can_evolve: bool = False
    ability_effects: list[dict] = field(default_factory=list)
    item_effects: list[dict] = field(default_factory=list)
    stat_override: dict | None = None   # para tests o stats leídos directamente del juego

    @property
    def stats(self) -> dict:
        if self.stat_override:
            return self.stat_override
        return calc_all(self.base_stats, self.level, self.ivs, self.evs, self.nature)

    def effects(self) -> list[dict]:
        return list(self.ability_effects) + list(self.item_effects)


def battler_from_set(dex, s: dict) -> Battler:
    """Construye un Battler a partir de un set (dict con species/ability/item/nature/moves...)."""
    sp = dex.species(s["species"]) if dex else None
    base = s.get("base_stats") or sp["base_stats"]
    return Battler(
        name=s.get("species", "?"),
        types=s.get("types") or sp["types"],
        base_stats=base,
        ability=s.get("ability"),
        item=s.get("item"),
        nature=s.get("nature", "Serious"),
        level=s.get("level", dex.rules.get("nivel", 49) if dex else 49),
        ivs=s.get("ivs") or (sp or {}).get("ivs", {}),
        evs=s.get("evs", {}),
        moves=s.get("moves", []),
        stages=dict(s.get("stages", {})),
        status=s.get("status"),
        can_evolve=s.get("can_evolve", (sp or {}).get("can_evolve", False)),
        ability_effects=s.get("ability_effects") if s.get("ability_effects") is not None
        else (dex.ability_effects(s.get("ability")) if dex else []),
        item_effects=s.get("item_effects") if s.get("item_effects") is not None
        else (dex.item_effects(s.get("item")) if dex else []),
    )


def _cond_ok(eff: dict, who: Battler, fld: dict, move: dict | None = None) -> bool:
    c = eff.get("condition")
    if not c:
        return True
    if c.startswith("weather:"):
        return fld.get("weather") == c.split(":", 1)[1]
    if c.startswith("terrain:"):
        return fld.get("terrain") == c.split(":", 1)[1]
    if c == "low_hp":
        return who.hp_frac <= 1 / 3
    if c == "full_hp":
        return who.hp_frac >= 1.0
    if c == "statused":
        return who.status is not None
    if c == "can_evolve":
        return who.can_evolve
    if c == "moves_last":
        return bool(fld.get("attacker_moves_last"))
    return bool(fld.get(c))


def _ignores_ability(att: Battler) -> bool:
    return any(e["kind"] == "ignore_ability" for e in att.ability_effects)


def effective_speed(b: Battler, fld: dict | None = None) -> int:
    fld = fld or {}
    spe = apply_stage(b.stats["spe"], b.stages.get("spe", 0))
    for e in b.effects():
        if e["kind"] == "speed_mult" and _cond_ok(e, b, fld):
            spe = math.floor(spe * e["mult"])
    if b.status == "par" and not any(e["kind"] == "ignore_par_speed" for e in b.effects()):
        spe = math.floor(spe * 0.5)
    if fld.get("trick_room"):
        return -spe
    return spe


def move_type_and_power(att: Battler, move: dict, fld: dict) -> tuple[str, float, bool]:
    """Devuelve (tipo final, potencia modificada por habilidad/objeto, convertido_por_habilidad)."""
    mtype = norm_type(move["type"])
    power = float(move.get("power") or 0)
    converted = False
    for e in att.ability_effects:
        if e["kind"] == "type_convert" and norm_type(e["from"]) == mtype and _cond_ok(e, att, fld):
            mtype = norm_type(e["to"])
            power *= e.get("mult", 1.0)
            converted = True
            break
    tags = set(move.get("tags", []))
    for e in att.effects():
        if e["kind"] == "power_mult" and _cond_ok(e, att, fld, move):
            if "max_bp" in e and (move.get("power") or 0) > e["max_bp"]:
                continue
            if "move_tag" in e and e["move_tag"] not in tags:
                continue
            if "category" in e and e["category"] != move["category"]:
                continue
            power *= e["mult"]
        elif e["kind"] == "type_power_mult" and norm_type(e["type"]) == mtype and _cond_ok(e, att, fld):
            power *= e["mult"]
        elif e["kind"] == "nonstab_power_mult" and mtype not in att.types:
            power *= e["mult"]  # Realeza (Añil): ataques que no son del tipo del usuario
    return mtype, power, converted


def calc(att: Battler, dfn: Battler, move: dict, fld: dict | None = None, crit: bool = False) -> dict:
    fld = fld or {}
    zero = {"min": 0, "max": 0, "min_pct": 0.0, "max_pct": 0.0, "eff": 0.0, "hits_to_ko": (99, 99), "type": move.get("type")}
    if move.get("category") == "status":
        return zero
    tags = set(move.get("tags", []))
    dhp = dfn.stats["hp"]

    mtype, power, converted = move_type_and_power(att, move, fld)
    eff = effectiveness(mtype, dfn.types)
    if fld.get("ring_target") and eff == 0:
        eff = 1.0

    # inmunidades / absorciones por habilidad u objeto del defensor
    def_effects = ([] if _ignores_ability(att) else dfn.ability_effects) + dfn.item_effects
    for e in def_effects:
        if e["kind"] == "immunity" and norm_type(e["type"]) == mtype:
            return {**zero, "type": mtype, "note": "inmune por habilidad/objeto"}
        if e["kind"] == "immunity_tag" and e["move_tag"] in tags:
            return {**zero, "type": mtype, "note": "inmune por habilidad"}
        if e["kind"] == "only_se_hits" and eff <= 1:
            return {**zero, "type": mtype, "note": "Superguarda"}
    if eff == 0:
        return {**zero, "type": mtype}

    # daño fijo
    if "fixed_level" in tags:
        d = att.level
        return {"min": d, "max": d, "min_pct": 100 * d / dhp, "max_pct": 100 * d / dhp, "eff": eff,
                "hits_to_ko": (math.ceil(dhp / d),) * 2, "type": mtype}

    physical = move["category"] == "physical"
    a_stat = "atk" if physical else "spa"
    d_stat = "def" if (physical or "target_def" in tags) else "spd"
    attacker_src = dfn if "foul_play" in tags else att
    if "body_press" in tags:
        a_stat = "def"

    a_stage = attacker_src.stages.get(a_stat, 0)
    d_stage = dfn.stages.get(d_stat, 0)
    ignore_def_stages = any(e["kind"] == "ignore_stages" for e in att.ability_effects)
    ignore_att_stages = any(e["kind"] == "ignore_stages" for e in (def_effects))
    if crit:
        a_stage = max(a_stage, 0)
        d_stage = min(d_stage, 0)
    A = apply_stage(attacker_src.stats[a_stat], 0 if ignore_att_stages else a_stage)
    D = apply_stage(dfn.stats[d_stat], 0 if ignore_def_stages else d_stage)

    for e in att.effects():
        if e["kind"] == "stat_mult" and e["stat"] == a_stat and _cond_ok(e, att, fld):
            A = math.floor(A * e["mult"])
    for e in def_effects:
        if e["kind"] == "defense_mult" and e["stat"] == d_stat and _cond_ok(e, dfn, fld):
            D = math.floor(D * e["mult"])
        if e["kind"] == "incoming_type_mult" and norm_type(e["type"]) == mtype:
            A = math.floor(A * e["mult"])
    if fld.get("weather") == "sand" and "Rock" in dfn.types and d_stat == "spd":
        D = math.floor(D * 1.5)
    if fld.get("weather") == "snow" and "Ice" in dfn.types and d_stat == "def":
        D = math.floor(D * 1.5)
    D = max(1, D)

    base = math.floor(math.floor(math.floor(2 * att.level / 5 + 2) * power * A / D) / 50) + 2

    def pround(x: float) -> int:  # redondeo "pokeRound": .5 hacia abajo
        return math.floor(x) + (1 if x - math.floor(x) > 0.5 else 0)

    pre = 1.0
    w = fld.get("weather")
    if w == "rain":
        pre *= 1.5 if mtype == "Water" else 0.5 if mtype == "Fire" else 1
    elif w == "sun":
        pre *= 1.5 if mtype == "Fire" else 0.5 if mtype == "Water" else 1
    if crit:
        pre *= 1.5

    stab = 1.0
    stab_all = any(e["kind"] == "stab_all" for e in att.ability_effects)
    if mtype in att.types or stab_all:
        stab = 1.5
        for e in att.ability_effects:
            if e["kind"] == "stab_mult":
                stab = e["mult"]
    burn = physical and att.status == "brn" and not any(e["kind"] == "ignore_burn" for e in att.effects())

    final = 1.0
    for e in att.effects():
        if e["kind"] == "final_mult" and _cond_ok(e, att, fld):
            final *= e["mult"]
        elif e["kind"] == "se_power_mult" and eff > 1:
            final *= e["mult"]
        elif e["kind"] == "nve_power_mult" and eff < 1:
            final *= e["mult"]
    for e in def_effects:
        if e["kind"] == "incoming_se_mult" and eff > 1:
            final *= e["mult"]
        elif e["kind"] == "incoming_full_hp_mult" and dfn.hp_frac >= 1.0:
            final *= e["mult"]
        elif e["kind"] == "incoming_category_mult" and e["category"] == move["category"]:
            final *= e["mult"]
        elif e["kind"] == "resist_berry" and norm_type(e["type"]) == mtype and eff > 1:
            final *= 0.5

    hits = 1
    mh = move.get("multi_hit")
    if mh:
        lo, hi = (mh, mh) if isinstance(mh, int) else mh
        skill_link = any(e["kind"] == "max_hits" for e in att.effects())
        hits = hi if skill_link else (lo if lo == hi else 3 if hi == 5 else hi)

    b2 = pround(base * pre)
    rolls = []
    for r in range(85, 101):
        d = math.floor(b2 * r / 100)
        d = pround(d * stab)
        d = math.floor(d * eff)
        if burn:
            d = math.floor(d * 0.5)
        d = pround(d * final)
        rolls.append(max(1, d) * hits)
    dmin, dmax = rolls[0], rolls[-1]
    hp_left = dhp * dfn.hp_frac
    return {
        "min": dmin, "max": dmax, "rolls": rolls,
        "min_pct": round(100 * dmin / dhp, 1), "max_pct": round(100 * dmax / dhp, 1),
        "eff": eff, "type": mtype, "hits": hits,
        "hits_to_ko": (math.ceil(hp_left / dmax), math.ceil(hp_left / dmin)),
    }


def best_move(att: Battler, dfn: Battler, dex, fld: dict | None = None) -> tuple[str | None, dict]:
    best, best_r = None, {"max_pct": 0.0, "min_pct": 0.0, "hits_to_ko": (99, 99)}
    for m in att.moves:
        md = dex.move(m) if dex else None
        if not md or md.get("category") == "status":
            continue
        r = calc(att, dfn, md, fld)
        acc = (md.get("accuracy") or 100) / 100
        score = (r["min_pct"] + r["max_pct"]) / 2 * acc
        best_score = (best_r["min_pct"] + best_r["max_pct"]) / 2 * best_r.get("acc", 1)
        if score > best_score:
            best, best_r = m, {**r, "acc": acc}
    return best, best_r
