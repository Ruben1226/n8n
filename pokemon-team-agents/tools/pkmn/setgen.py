"""Generador de sets candidatos por Pokémon (determinista).

Para cada Pokémon × habilidad genera hasta 3 arquetipos (atacante, setup, soporte/pivote),
cada uno con variante "sin menta" (naturaleza actual) y "con menta" (naturaleza ideal) si difieren.
El agente evaluador-individual revisa y corrige estos sets: esto es un punto de partida sólido, no la verdad.
"""
from __future__ import annotations

import math

from .data import Dex, key
from .damage import move_type_and_power, Battler
from .stats import calc_all, NATURES, norm_nature
from .typechart import all_type_combos, effectiveness, TYPES

COMBOS = all_type_combos()

UTILITY_PRIORITY = [
    # (tag, valor base) – el orden importa al rellenar huecos
    ("hazard_set", 3.0), ("recovery", 3.0), ("hazard_remove", 2.5), ("pivot", 2.5),
    ("status_burn", 2.0), ("status_para", 2.0), ("status_toxic", 2.0), ("status_sleep", 2.0),
    ("speed_control", 2.0), ("phaze", 1.5), ("screens", 1.5), ("taunt", 1.2), ("protect", 0.8),
    ("cleric", 1.2), ("trick", 1.2),
]
SETUP_TAGS = {"physical": ["setup_atk", "setup_mixed"], "special": ["setup_spa", "setup_mixed"]}
MOVE_PENALTY = {"recharge": 0.5, "charge": 0.55, "self_ko": 0.3, "self_drop": 0.88, "recoil": 0.93,
                "lock_in": 0.9, "unreliable": 0.7}

ITEM_PREFS = {
    "atacante_physical": ["Choice Band", "Life Orb", "Choice Scarf", "Expert Belt"],
    "atacante_special": ["Choice Specs", "Life Orb", "Choice Scarf", "Expert Belt"],
    "setup": ["Life Orb", "Leftovers", "Sitrus Berry", "Lum Berry", "Weakness Policy"],
    "soporte": ["Eviolite", "Leftovers", "Rocky Helmet", "Heavy-Duty Boots", "Sitrus Berry", "Assault Vest"],
}


def _effective_power(dex: Dex, b: Battler, md: dict) -> tuple[str, float]:
    mtype, power, _ = move_type_and_power(b, md, {})
    if "fixed_level" in md.get("tags", []):
        power = 60.0  # aprox: a nivel 49 ~ 49 PS fijos
    stab = 1.0
    if mtype in b.types or any(e["kind"] == "stab_all" for e in b.ability_effects):
        stab = 1.5
        for e in b.ability_effects:
            if e["kind"] == "stab_mult":
                stab = e["mult"]
    acc = (md.get("accuracy") or 100) / 100
    mh = md.get("multi_hit")
    hits = 1
    if mh:
        lo, hi = (mh, mh) if isinstance(mh, int) else mh
        hits = hi if any(e["kind"] == "max_hits" for e in b.effects()) else (lo if lo == hi else (3 if hi == 5 else hi))
    pen = 1.0
    for t in md.get("tags", []):
        pen *= MOVE_PENALTY.get(t, 1.0)
    prio = 1.08 if md.get("priority", 0) > 0 else 1.0
    return mtype, power * stab * acc * hits * pen * prio


def _coverage_value(attacks: list[tuple[str, float]]) -> float:
    """Media sobre todas las combinaciones de tipos de log(1 + mejor golpe/100)."""
    if not attacks:
        return 0.0
    tot = 0.0
    for combo in COMBOS:
        best = max(ep * effectiveness(t, list(combo)) for t, ep in attacks)
        tot += math.log1p(best / 100)
    return tot / len(COMBOS)


def _pick_coverage(cands: list[tuple[str, str, float]], k: int) -> list[tuple[str, str, float]]:
    chosen: list[tuple[str, str, float]] = []
    pool = list(cands)
    while pool and len(chosen) < k:
        base = _coverage_value([(t, ep) for _, t, ep in chosen])
        best, gain = None, 0.0
        for c in pool:
            g = _coverage_value([(t, ep) for _, t, ep in chosen] + [(c[1], c[2])]) - base
            if g > gain:
                best, gain = c, g
        if best is None or gain < 0.005:
            break
        chosen.append(best)
        pool.remove(best)
    return chosen


def _ideal_nature(role: str, lean: str, base: dict, fast: bool) -> str:
    unused = "spa" if lean == "physical" else "atk"
    if role in ("atacante", "setup"):
        if lean == "mixed":
            weak_def = "def" if base["def"] < base["spd"] else "spd"
            up = "spe" if fast else ("atk" if base["atk"] >= base["spa"] else "spa")
            return _nature_for(up, weak_def)
        up = "spe" if fast else ("atk" if lean == "physical" else "spa")
        return _nature_for(up, unused)
    # soporte: refuerza la defensa más baja
    up = "def" if base["def"] * 1.0 <= base["spd"] else "spd"
    return _nature_for(up, unused if lean != "mixed" else "spe")


def _nature_for(up: str, down: str) -> str:
    for n, (u, d) in NATURES.items():
        if u == up and d == down:
            return n
    return "Serious"


def _same_effect(n1: str, n2: str) -> bool:
    return NATURES[norm_nature(n1)] == NATURES[norm_nature(n2)] or (
        NATURES[norm_nature(n1)][0] is None and NATURES[norm_nature(n2)][0] is None)


def _nature_value(nature: str, role: str, lean: str, fast: bool) -> float:
    """Valor aproximado de una naturaleza para un rol (pesos por stat)."""
    w = {"hp": 0, "atk": 0.0, "def": 0.3, "spa": 0.0, "spd": 0.3, "spe": 0.8 if fast else 0.4}
    if role in ("atacante", "setup"):
        if lean in ("physical", "mixed"):
            w["atk"] = 1.0
        if lean in ("special", "mixed"):
            w["spa"] = 1.0
    else:
        w.update({"def": 0.8, "spd": 0.8, "spe": 0.3})
        if lean in ("physical", "mixed"):
            w["atk"] = 0.4
        if lean in ("special", "mixed"):
            w["spa"] = 0.4
    up, down = NATURES[norm_nature(nature)]
    return (w.get(up, 0) * 0.1 if up else 0) - (w.get(down, 0) * 0.1 if down else 0)


TYPE_BOOSTERS = {
    "Fire": ["Charcoal", "Flame Plate", "Fire Gem"], "Water": ["Mystic Water", "Splash Plate", "Water Gem"],
    "Electric": ["Magnet", "Zap Plate", "Electric Gem"], "Grass": ["Miracle Seed", "Meadow Plate", "Grass Gem"],
    "Ice": ["Never-Melt Ice", "Icicle Plate", "Ice Gem"], "Fighting": ["Black Belt", "Fist Plate", "Fighting Gem"],
    "Poison": ["Poison Barb", "Toxic Plate", "Poison Gem"], "Ground": ["Soft Sand", "Earth Plate", "Ground Gem"],
    "Flying": ["Sharp Beak", "Sky Plate", "Flying Gem"], "Psychic": ["Twisted Spoon", "Mind Plate", "Psychic Gem"],
    "Bug": ["Silver Powder", "Insect Plate", "Bug Gem"], "Rock": ["Hard Stone", "Stone Plate", "Rock Gem"],
    "Ghost": ["Spell Tag", "Spooky Plate", "Ghost Gem"], "Dragon": ["Dragon Fang", "Draco Plate", "Dragon Gem"],
    "Dark": ["Black Glasses", "Dread Plate", "Dark Gem"], "Steel": ["Metal Coat", "Iron Plate", "Steel Gem"],
    "Fairy": ["Fairy Feather", "Pixie Plate", "Fairy Gem"], "Normal": ["Silk Scarf", "Normal Gem"],
}
RESIST_BERRY = {"Fire": "Occa Berry", "Water": "Passho Berry", "Electric": "Wacan Berry", "Grass": "Rindo Berry",
                "Ice": "Yache Berry", "Fighting": "Chople Berry", "Poison": "Kebia Berry", "Ground": "Shuca Berry",
                "Flying": "Coba Berry", "Psychic": "Payapa Berry", "Bug": "Tanga Berry", "Rock": "Charti Berry",
                "Ghost": "Kasib Berry", "Dragon": "Haban Berry", "Dark": "Colbur Berry", "Steel": "Babiri Berry",
                "Fairy": "Roseli Berry"}


def item_candidates(dex: Dex, mon: dict, role: str, lean: str, moves: list[str], ability: str, st: dict, k: int = 2) -> list[str]:
    """Los k mejores objetos DISPONIBLES para el set (puntuación heurística; el arquitecto/crítico afinan)."""
    avail = {key(i["name"]): i["name"] for i in dex.available_items()}
    unrestricted = not avail
    mds = [dex.move(m) or {} for m in moves]
    tags = {t for md in mds for t in md.get("tags", [])}
    has_status = any(md.get("category") == "status" for md in mds)
    ab = key(ability or "")
    sc: dict[str, float] = {}

    def add(name, v):
        sc[name] = max(sc.get(name, 0), v)

    off = role in ("atacante", "setup")
    if off:
        add("Life Orb", 3.0 + (1.0 if ab == "magicguard" else 0))
        add("Expert Belt", 2.3)
        if not has_status:
            add("Choice Band" if lean != "special" else "Choice Specs", 3.2)
            add("Choice Scarf", 2.6)
    if role == "setup":
        add("Weakness Policy", 2.4)
        add("Lum Berry", 2.2)
    add("Leftovers", 3.0 if role == "soporte" else 2.0)
    if "Poison" in mon["types"]:
        add("Black Sludge", 3.0 if role == "soporte" else 2.0)
    if mon.get("can_evolve"):
        add("Eviolite", 3.6 if role == "soporte" else 2.4)
    if role == "soporte":
        add("Rocky Helmet", 2.0)
        add("Covert Cloak", 1.0)
        add("Eject Button", 0.9)
    if "screens" in tags:
        add("Light Clay", 3.2)
    if any(isinstance(md.get("multi_hit"), list) and md["multi_hit"][0] != md["multi_hit"][1] for md in mds):
        add("Loaded Dice", 2.9)  # solo sirve con multigolpe VARIABLE (2-5), no con golpes fijos (Doble Ala...)
    if ab in ("poisonheal", "toxicboost"):
        add("Toxic Orb", 3.8)
    if ab in ("guts", "flareboost", "marvelscale"):
        add("Flame Orb", 3.6)
    if ab in ("superluck", "sniper"):
        add("Scope Lens", 2.5)
        add("Razor Claw", 2.5)
    if any("drain" in md.get("tags", []) for md in mds):
        add("Big Root", 1.0)
    # potenciador del tipo del ataque principal
    attacks = [md for md in mds if md.get("category") in ("physical", "special") and md.get("power")]
    if attacks:
        main = max(attacks, key=lambda md: (md.get("power") or 0) * (1.5 if md["type"] in mon["types"] else 1))
        for i, it in enumerate(TYPE_BOOSTERS.get(main["type"], [])):
            add(it, (2.4 if off else 1.0) - (0.6 if it.endswith("Gem") else 0) - 0.01 * i)
    # baya de resistencia a la peor debilidad
    from .typechart import effectiveness as _eff
    weak = sorted(((t, _eff(t, mon["types"])) for t in RESIST_BERRY), key=lambda x: -x[1])
    if weak and weak[0][1] >= 2:
        add(RESIST_BERRY[weak[0][0]], 1.8 if weak[0][1] >= 4 else 1.4)
    if _eff("Ground", mon["types"]) >= 2:
        add("Air Balloon", 1.3)
    add("Focus Sash", 1.6 if (role == "soporte" and "hazard_set" in tags) else 0.8)
    add("Focus Band", 0.5)
    ranked = sorted(sc.items(), key=lambda x: -x[1])
    out = []
    for name, _ in ranked:
        if unrestricted or key(name) in avail:
            out.append(avail.get(key(name), name))
        if len(out) >= k:
            break
    return out


def _pick_item(dex: Dex, prefs: list[str], can_evolve: bool) -> str | None:
    avail = {key(i["name"]): i["name"] for i in dex.available_items()}
    restrict = bool(avail)
    for p in prefs:
        if p == "Eviolite" and not can_evolve:
            continue
        if not restrict or key(p) in avail:
            return avail.get(key(p), p)
    return None


def generate_for(dex: Dex, mon: dict, speed_threshold: int) -> list[dict]:
    level = mon.get("level") or dex.rules.get("nivel", 49)
    legal = [dex.move(m) for m in dex.legal_moves(mon)]
    legal = [m for m in legal if m]
    sets: list[dict] = []
    abilities = mon.get("abilities", [])
    if not dex.rules.get("habilidad_cambiable", True) and mon.get("current_ability"):
        abilities = [mon["current_ability"]]
    banned_ab = {key(a) for a in dex.rules.get("habilidades_sin_efecto_en_showdown", [])}
    usable_ab = [a for a in abilities if key(a) not in banned_ab]
    abilities = usable_ab or abilities[:1]
    for ability in abilities:
        b = Battler(mon["name"], mon["types"], mon["base_stats"], ability=ability, level=level,
                    ivs=mon.get("ivs", {}), can_evolve=mon.get("can_evolve", False),
                    ability_effects=dex.ability_effects(ability))
        st = calc_all(mon["base_stats"], level, mon.get("ivs", {}), {}, "Serious")
        phys, spec = [], []
        for md in legal:
            if md["category"] == "status":
                continue
            t, ep = _effective_power(dex, b, md)
            if ep <= 0:
                continue
            (phys if md["category"] == "physical" else spec).append((md["name"], t, ep))
        top = lambda xs: sum(sorted((e for *_, e in xs), reverse=True)[:3])
        p_score = top(phys) * st["atk"]
        s_score = top(spec) * st["spa"]
        if p_score and s_score and 0.85 <= p_score / s_score <= 1.18:
            lean = "mixed"
        else:
            lean = "physical" if p_score >= s_score else "special"
        stat_of = {"physical": st["atk"], "special": st["spa"]}
        attacks = [(n, t, ep * stat_of["physical"] / 100) for n, t, ep in phys] + \
                  [(n, t, ep * stat_of["special"] / 100) for n, t, ep in spec]
        if lean != "mixed":
            main = phys if lean == "physical" else spec
            off = spec if lean == "physical" else phys
            # se permite un ataque de la otra categoría solo si es mucho mejor en cobertura
            attacks = [(n, t, ep * stat_of[lean] / 100) for n, t, ep in main] + \
                      [(n, t, ep * stat_of["special" if lean == "physical" else "physical"] / 100 * 0.8) for n, t, ep in off]

        util: dict[str, list[str]] = {}
        for md in legal:
            for tag in md.get("tags", []):
                util.setdefault(tag, []).append(md["name"])
        fast = st["spe"] >= speed_threshold
        archetypes = []

        atk4 = _pick_coverage(attacks, 4)
        if atk4:
            archetypes.append(("atacante", [a[0] for a in atk4]))

        setup_moves = [m for tg in SETUP_TAGS.get(lean if lean != "mixed" else "physical", []) for m in util.get(tg, [])]
        if setup_moves:
            atk3 = _pick_coverage(attacks, 3)
            if atk3:
                # mejor movimiento de setup: prioriza los que suben también velocidad
                sm = sorted(setup_moves, key=lambda m: ("setup_spe" in dex.move(m).get("tags", []), m), reverse=True)[0]
                archetypes.append(("setup", [sm] + [a[0] for a in atk3]))

        util_moves = []
        for tag, _ in UTILITY_PRIORITY:
            for m in util.get(tag, []):
                if m not in util_moves:
                    util_moves.append(m)
                    break
            if len(util_moves) >= 2:
                break
        bulk = (st["hp"] * (st["def"] + st["spd"]) / 2)
        if len(util_moves) >= 1:
            atk2 = _pick_coverage(attacks, 4 - len(util_moves))
            archetypes.append(("soporte", util_moves + [a[0] for a in atk2]))

        ranked_attacks = [n for n, _, _ in sorted(attacks, key=lambda x: -x[2])]
        other_util = [m for tag, _ in UTILITY_PRIORITY for m in util.get(tag, [])]

        def _pad(role: str, moves: list[str]) -> list[str]:
            if role == "atacante":
                order = util.get("pivot", []) + ranked_attacks + other_util
            else:
                order = other_util + ranked_attacks
            out = list(moves)
            for m in order:
                if len(out) >= 4:
                    break
                if m not in out:
                    out.append(m)
            return out

        for role, moves in archetypes:
            moves = _pad(role, moves)
            current = mon.get("nature") or "Serious"
            if mon.get("fixed_item"):
                items = [mon["fixed_item"]]
            else:
                items = item_candidates(dex, mon, role, lean, moves, ability, st) or [None]
            variants = [(current, False)]
            mint_stock = dex.rules.get("mentas")
            if isinstance(mint_stock, dict):
                # mentas de naturaleza CONCRETA: solo se ofrecen las que el jugador tiene y mejoran el set
                for nat, qty in mint_stock.items():
                    if qty > 0 and not _same_effect(nat, current) and \
                            _nature_value(nat, role, lean, fast) > _nature_value(current, role, lean, fast) + 0.01:
                        variants.append((norm_nature(nat), True))
            else:
                ideal = _ideal_nature(role, lean, mon["base_stats"], fast)
                if not _same_effect(ideal, current):
                    variants.append((ideal, True))
            for item in items:
                for nature, needs_mint in variants:
                    sets.append(build_set(dex, mon, ability, item, nature, moves, role, lean, needs_mint))
    return sets


def role_tags(dex: Dex, s: dict, speed_threshold: int) -> list[str]:
    tags = set()
    for m in s["moves"]:
        md = dex.move(m) or {}
        mt = set(md.get("tags", []))
        tags |= mt & {"hazard_set", "hazard_remove", "pivot", "recovery", "phaze", "screens", "cleric",
                      "status_burn", "status_para", "status_toxic", "status_sleep", "taunt", "trick"}
        if mt & {"setup_atk", "setup_spa", "setup_mixed", "setup_spe"}:
            tags.add("setup_wincon")
        if md.get("priority", 0) > 0 and md.get("category") != "status":
            tags.add("priority")
        if "speed_control" in mt or "status_para" in mt:
            tags.add("speed_control")
    if s["stats"]["spe"] >= speed_threshold or (s.get("item") or "").lower() == "choice scarf" or "priority" in tags:
        tags.add("speed_control" if (s.get("item") or "").lower() == "choice scarf" or "priority" in tags else "fast")
        if s["stats"]["spe"] >= speed_threshold:
            tags.add("fast")
    if any(t.startswith("status_") for t in tags):
        tags.add("status_spreader")
    for e in s["ability_effects"]:
        if e["kind"] == "immunity":
            tags.add(f"immune_{e['type']}")
        if e["kind"] == "on_switch_in":
            tags.add(f"switchin_{e.get('effect')}")
    return sorted(tags)


def _showdown_equivalents(dex: Dex, ability, item, moves) -> dict:
    """Copia los equivalentes de Showdown que fijó el oráculo (campo showdown_equivalent) para cosas de Añil."""
    out = {}
    a = dex.abilities.get(key(ability)) if ability else None
    if a and a.get("showdown_equivalent"):
        out["showdown_ability"] = a["showdown_equivalent"]
    i = dex.items.get(key(item)) if item else None
    if i and i.get("showdown_equivalent"):
        out["showdown_item"] = i["showdown_equivalent"]
    mm = {m: dex.move(m)["showdown_equivalent"] for m in moves if (dex.move(m) or {}).get("showdown_equivalent")}
    if mm:
        out["showdown_moves"] = mm
    return out


def build_set(dex: Dex, mon: dict, ability: str, item: str | None, nature: str, moves: list[str],
              role: str, lean: str, needs_mint: bool) -> dict:
    level = mon.get("level") or dex.rules.get("nivel", 49)
    # nombres canónicos (inglés) para que el simulador de Showdown los reconozca
    ab_entry = dex.abilities.get(key(ability)) if ability else None
    ability = ab_entry["name"] if ab_entry else ability
    it_entry = dex.items.get(key(item)) if item else None
    item = it_entry["name"] if it_entry else item
    moves = [(dex.move(m) or {}).get("name", m) for m in moves]
    st = calc_all(mon["base_stats"], level, mon.get("ivs", {}), {}, nature)
    b = Battler(mon["name"], mon["types"], mon["base_stats"], ability=ability, item=item, level=level,
                ivs=mon.get("ivs", {}), nature=nature, can_evolve=mon.get("can_evolve", False),
                ability_effects=dex.ability_effects(ability), item_effects=dex.item_effects(item))
    attacks = []
    for m in moves:
        md = dex.move(m)
        if md and md["category"] != "status":
            t, ep = _effective_power(dex, b, md)
            stat = st["atk"] if md["category"] == "physical" else st["spa"]
            for e in b.effects():
                if e["kind"] == "stat_mult" and e["stat"] == ("atk" if md["category"] == "physical" else "spa") and not e.get("condition"):
                    stat *= e["mult"]
                if e["kind"] == "final_mult" and not e.get("condition"):
                    ep *= e["mult"]
            attacks.append((t, ep * stat / 100))
    hp_def = st["hp"] * st["def"]
    hp_spd = st["hp"] * st["spd"]
    for e in b.effects():
        if e["kind"] == "defense_mult" and (not e.get("condition") or (e["condition"] == "can_evolve" and b.can_evolve)):
            if e["stat"] == "def":
                hp_def *= e["mult"]
            else:
                hp_spd *= e["mult"]
    ref = calc_all({k: 80 for k in ("hp", "atk", "def", "spa", "spd", "spe")}, level)
    ref_bulk = ref["hp"] * ref["def"]
    s = {
        "id": f"{mon['name']}|{ability}|{role}|{nature}",
        "species": mon["name"], "species_key": mon.get("mega_de") or mon["name"],
        "needs_seta": bool(mon.get("current_ability")) and key(ability or "") != key(mon.get("current_ability") or "")
                      and not mon.get("fixed_item"),
        "types": mon["types"], "base_stats": mon["base_stats"],
        **({"showdown_species": mon["showdown_name"]} if mon.get("showdown_name") else {}),
        **({"showdown_ability": mon["sd_set_ability"]} if mon.get("sd_set_ability") else {}),
        **_showdown_equivalents(dex, ability, item, moves),
        "ivs": mon.get("ivs", {}), "can_evolve": mon.get("can_evolve", False),
        "ability": ability, "ability_effects": dex.ability_effects(ability),
        "item": item, "item_effects": dex.item_effects(item),
        "nature": nature, "needs_mint": needs_mint, "role": role, "lean": lean,
        "moves": moves, "stats": st, "level": level,
        "scores": {
            "offense": round(_coverage_value(attacks) * 10, 3),
            "phys_bulk": round(hp_def / ref_bulk, 3),
            "spec_bulk": round(hp_spd / ref_bulk, 3),
            "speed": st["spe"],
        },
    }
    return s


def speed_threshold(dex: Dex) -> int:
    level = dex.rules.get("nivel", 49)
    speeds = sorted(calc_all(p["base_stats"], p.get("level") or level, p.get("ivs", {}))["spe"] for p in dex.pokemon) or [100]
    return speeds[int(len(speeds) * 0.6)]


def score_set(dex: Dex, s: dict, threshold: int) -> dict:
    """(Re)calcula role_tags y puntuaciones de un set (también sirve para sets editados a mano)."""
    sp = dex.species(s["species"]) or {}
    mon = dict(sp)  # conserva level, current_ability, mega_de, fixed_item, sd_set_ability...
    mon.update({"name": s["species"], "types": s.get("types") or sp.get("types"), "base_stats": s.get("base_stats") or sp.get("base_stats"),
                "ivs": s.get("ivs") or sp.get("ivs", {}), "can_evolve": s.get("can_evolve", sp.get("can_evolve", False)),
                "showdown_name": s.get("showdown_species") or sp.get("showdown_name")})
    if s.get("level"):
        mon["level"] = s["level"]
    fresh = build_set(dex, mon, s["ability"], s.get("item"), s.get("nature", "Serious"), s["moves"],
                      s.get("role", "atacante"), s.get("lean", "physical"), s.get("needs_mint", False))
    for k, v in s.items():  # conservar campos extra (origen, notas, showdown_*...)
        if k not in fresh:
            fresh[k] = v
    fresh["id"] = s.get("id", fresh["id"])
    fresh["role_tags"] = role_tags(dex, fresh, threshold)
    util = sum(v for tg, v in UTILITY_PRIORITY if tg in fresh["role_tags"])
    sc = fresh["scores"]
    sc["utility"] = round(util, 2)
    bulk = (sc["phys_bulk"] + sc["spec_bulk"]) / 2
    spd_factor = min(1.5, sc["speed"] / threshold)
    if fresh["role"] == "soporte":
        sc["total"] = round(bulk * 4 + util * 0.8 + sc["offense"] * 0.8, 3)
    else:
        sc["total"] = round(sc["offense"] * (0.7 + 0.5 * spd_factor) + bulk * 1.5 + util * 0.3, 3)
    return fresh


def add_percentiles(sets: list[dict]) -> None:
    """Percentil de cada set DENTRO de su rol (atacante / setup / soporte): hace comparables los roles."""
    by_role: dict[str, list[dict]] = {}
    for s in sets:
        by_role.setdefault(s.get("role", "atacante"), []).append(s)
    for group in by_role.values():
        group.sort(key=lambda s: s["scores"]["total"])
        n = len(group)
        for i, s in enumerate(group):
            s["scores"]["percentil_rol"] = round((i + 1) / n, 3) if n > 1 else 1.0


def rescore_all(dex: Dex, sets: list[dict]) -> list[dict]:
    thr = speed_threshold(dex)
    out = [score_set(dex, s, thr) for s in sets]
    add_percentiles(out)
    out.sort(key=lambda s: s["scores"]["total"], reverse=True)
    return out


def generate_all(dex: Dex):
    threshold = speed_threshold(dex)
    out = []
    for mon in dex.pokemon:
        for s in generate_for(dex, mon, threshold):
            out.append(score_set(dex, s, threshold))
    add_percentiles(out)
    out.sort(key=lambda s: s["scores"]["total"], reverse=True)
    return out, threshold
