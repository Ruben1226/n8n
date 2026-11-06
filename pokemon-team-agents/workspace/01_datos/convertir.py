"""Convierte pokemon_anil_base_datos.json (exportado de la partida) al formato del motor.

Decisión clave: los combates se juegan en Pokémon Showdown [Gen 9] Custom Game, que usa los tipos y
stats OFICIALES de Showdown (no se pueden cambiar). Por eso base_stats/types = Showdown; los de Añil se
conservan en base_stats_anil/types_anil como información.
Uso: python workspace/01_datos/convertir.py <fichero_partida.json>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(sys.argv[1], encoding="utf-8"))
ref = json.load(open(os.path.join(HERE, "showdown_ref.json"), encoding="utf-8"))

ST = {"PS": "hp", "Ataque": "atk", "Defensa": "def", "At. Esp.": "spa", "Def. Esp.": "spd", "Velocidad": "spe"}
NAT = {"HARDY": "Hardy", "LONELY": "Lonely", "BRAVE": "Brave", "ADAMANT": "Adamant", "NAUGHTY": "Naughty", "BOLD": "Bold",
       "DOCILE": "Docile", "RELAXED": "Relaxed", "IMPISH": "Impish", "LAX": "Lax", "TIMID": "Timid", "HASTY": "Hasty",
       "SERIOUS": "Serious", "JOLLY": "Jolly", "NAIVE": "Naive", "MODEST": "Modest", "MILD": "Mild", "QUIET": "Quiet",
       "BASHFUL": "Bashful", "RASH": "Rash", "CALM": "Calm", "GENTLE": "Gentle", "SASSY": "Sassy", "CAREFUL": "Careful",
       "QUIRKY": "Quirky"}
TY = {"Normal": "Normal", "Fuego": "Fire", "Agua": "Water", "Eléctrico": "Electric", "Planta": "Grass", "Hielo": "Ice",
      "Lucha": "Fighting", "Veneno": "Poison", "Tierra": "Ground", "Volador": "Flying", "Psíquico": "Psychic", "Bicho": "Bug",
      "Roca": "Rock", "Fantasma": "Ghost", "Dragón": "Dragon", "Siniestro": "Dark", "Acero": "Steel", "Hada": "Fairy"}
# Habilidades exclusivas de Añil: cómo quedan en Showdown
CUSTOM_AB = {
    "REALEZA": {"showdown_equivalent": "Adaptability",
                "nota": "El exportador a Showdown la convierte en Adaptability: en el combate real es Adaptable (STAB x2)."},
    "ASONECHILLINGNEIGH": {"showdown_equivalent": "As One (Glastrier)", "nota": "Existe en Showdown como As One (Glastrier)."},
}

ID2MOVE = {k: v for k, v in ref["moves"].items() if v.get("exists", True)}


def mv(m):
    r = ID2MOVE.get(m["id"])
    return r["name"] if r else None


def tags_of(r):
    t = set()
    f = r.get("flags") or {}
    for flag, tag in (("contact", "contact"), ("punch", "punch"), ("bite", "bite"), ("sound", "sound"), ("pulse", "pulse"),
                      ("slicing", "slicing"), ("bullet", "bullet"), ("charge", "charge"), ("recharge", "recharge")):
        if f.get(flag):
            t.add(tag)
    if r.get("secondaries"): t.add("secondary")
    if r.get("recoil"): t.add("recoil")
    if r.get("drain"): t.add("drain")
    if r.get("multihit"): t.add("multi_hit")
    sb = r.get("selfBoost") or (r.get("boosts") if r.get("target") == "self" else None) or {}
    if r["category"] != "Status" and r.get("selfBoost") and any(v < 0 for v in r["selfBoost"].values()):
        t.add("self_drop")
    if r["category"] == "Status" and sb:
        if sb.get("atk", 0) > 0: t.add("setup_atk")
        if sb.get("spa", 0) > 0: t.add("setup_spa")
        if sb.get("spe", 0) > 0: t.add("setup_spe")
        if sum(1 for k in ("atk", "spa", "spe") if sb.get(k, 0) > 0) >= 2 or (sb.get("spe", 0) > 0 and (sb.get("atk", 0) > 0 or sb.get("spa", 0) > 0)):
            t.add("setup_mixed")
    n = r["name"]
    if r.get("heal") or n in ("Rest", "Wish", "Roost", "Synthesis", "Moonlight", "Morning Sun", "Shore Up", "Strength Sap", "Leech Seed", "Life Dew"):
        if r["category"] == "Status": t.add("recovery")
    if r.get("sideCondition") in ("stealthrock", "spikes", "toxicspikes", "stickyweb"): t.add("hazard_set")
    if n in ("Rapid Spin", "Defog", "Mortal Spin", "Tidy Up", "Court Change"): t.add("hazard_remove")
    if r.get("selfSwitch") and n not in ("Baton Pass", "Shed Tail"): t.add("pivot")
    st = r.get("status")
    if r["category"] == "Status" and st:
        t.add({"brn": "status_burn", "par": "status_para", "tox": "status_toxic", "psn": "status_toxic", "slp": "status_sleep"}.get(st, "status_other"))
    if n == "Yawn": t.add("status_sleep")
    if r.get("forceSwitch") and r["category"] == "Status": t.add("phaze")
    if n in ("Haze", "Clear Smog"): t.add("phaze")
    if n in ("Reflect", "Light Screen", "Aurora Veil"): t.add("screens")
    if n == "Taunt": t.add("taunt")
    if n in ("Trick", "Switcheroo"): t.add("trick")
    if n in ("Protect", "Detect", "Spiky Shield", "Baneful Bunker", "King's Shield", "Silk Trap", "Burning Bulwark"): t.add("protect")
    if n in ("Thunder Wave", "Glare", "Stun Spore", "Nuzzle", "Tailwind", "Trick Room", "Sticky Web", "Icy Wind", "Electroweb", "Rock Tomb", "Bulldoze"): t.add("speed_control")
    if n in ("Heal Bell", "Aromatherapy"): t.add("cleric")
    if n in ("Seismic Toss", "Night Shade"): t.add("fixed_level")
    if r.get("overrideDef") == "def": t.add("target_def")
    if r.get("overrideOffPkmn") == "target": t.add("foul_play")
    if r.get("overrideOffStat") == "def": t.add("body_press")
    if n in ("Self-Destruct", "Explosion", "Misty Explosion", "Memento", "Final Gambit"): t.add("self_ko")
    if n in ("Outrage", "Thrash", "Petal Dance", "Raging Fury"): t.add("lock_in")
    if n in ("Focus Punch", "Dream Eater", "Belch", "Synchronoise", "Last Resort", "Fling", "Natural Gift", "Steel Roller", "Hold Back", "False Swipe", "Snore", "Spit Up", "Present", "Magnitude", "Fake Out", "First Impression", "Sucker Punch", "Burn Up", "Double Shock", "Future Sight", "Doom Desire"):
        t.add("unreliable")
    return sorted(t)


pokemon, moves, abilities = [], {}, {}
dropped = set()
for p in src["pokemon"]:
    sd = ref["species"][p["especie_id"]]
    learn = {"level_up": [], "relearn": [], "tm": [], "tutor": [], "egg": []}
    cur = []
    for group, dst in (("movimientos_actuales", None), ("recordador_ahora", "relearn"), ("mt_compatibles_que_tiene", "tm")):
        for m in p.get(group) or []:
            name = mv(m)
            if not name:
                dropped.add(m["id"]); continue
            (cur if dst is None else learn[dst]).append(name)
            r = ID2MOVE[m["id"]]
            if name not in moves:
                acc = None if r["accuracy"] is True else r["accuracy"]
                mh = r.get("multihit")
                moves[name] = {"name": name, "name_es": m["nombre"], "type": r["type"], "category": r["category"].lower(),
                               "power": r["basePower"] or None, "accuracy": acc, "pp": r["pp"], "priority": r["priority"],
                               "tags": tags_of(r), **({"multi_hit": mh} if mh else {}), "effect": r.get("shortDesc"),
                               **({"note_anil": "datos de Añil distintos (en Showdown mandan estos)"} if (m.get("potencia") or 0) != (r["basePower"] or 0) and m.get("potencia") else {})}
    abil = []
    for a in p["habilidad"]["posibles"]:
        ra = ref["abilities"][a["id"]]
        if ra.get("exists", True):
            nm = ra["name"]
        else:
            nm = CUSTOM_AB.get(a["id"], {}).get("showdown_equivalent") if a["id"] in CUSTOM_AB else a["nombre"]
        abil.append(nm)
        if nm not in abilities:
            e = {"name": nm, "name_es": a["nombre"], "description": a["descripcion"]}
            if not ra.get("exists", True) and a["id"] not in CUSTOM_AB:
                e.update({"effects": [{"kind": "note", "text": "Exclusiva de Añil: NO existe en Showdown (sin efecto en combate)"}],
                          "custom_anil": True, "sin_efecto_en_showdown": True})
            if a["id"] in CUSTOM_AB:
                e["nota"] = CUSTOM_AB[a["id"]]["nota"]
            abilities[nm] = e
    act = p["habilidad"]["actual"]["id"]
    ra = ref["abilities"].get(act, {})
    cur_ab = ra["name"] if ra.get("exists", True) and ra else CUSTOM_AB.get(act, {}).get("showdown_equivalent", p["habilidad"]["actual"]["nombre"])
    ivs = {ST[k]: v for k, v in p["IVs"].items()}
    entry = {
        "name": sd["name"], "name_es": p["especie"], "mote": p["mote"], "level": p["nivel"],
        "types": sd["types"], "base_stats": sd["baseStats"],
        "types_anil": [TY[t] for t in p["tipos"]], "base_stats_anil": {ST[k]: v for k, v in p["stats_base_anil"].items()},
        "abilities": abil, "current_ability": cur_ab, "nature": NAT[p["naturaleza"]["id"]], "ivs": ivs,
        "can_evolve": bool(p.get("evoluciona")), "current_moves": cur, "learnset": learn,
        "en_equipo": p.get("en_equipo", False), "ubicacion": p.get("ubicacion"),
    }
    pokemon.append(entry)
    if sd["name"] == "Charizard" and "MEGA_Charizardite X" in ref["items"]:
        mx = ref["mega"]
        mega = dict(entry, name="Charizard-Mega-X", showdown_name="Charizard", mega_de="Charizard", types=mx["types"],
                    base_stats=mx["baseStats"], abilities=["Tough Claws"], current_ability="Tough Claws",
                    fixed_item="Charizardite X", sd_set_ability=entry["current_ability"], can_evolve=False)
        pokemon.append(mega)
        abilities.setdefault("Tough Claws", {"name": "Tough Claws"})

items = []
for k, v in ref["items"].items():
    if k.startswith("MEGA_"):
        continue
    items.append({"name": v["name"], "quantity": v["qty"], "description": v["desc"]})
if any(p["name"] == "Charizard-Mega-X" for p in pokemon):
    items.append({"name": "Charizardite X", "quantity": 1, "description": "Megapiedra (Megaaro disponible)"})

for f, obj in (("pokemon", pokemon), ("moves", list(moves.values())), ("abilities", list(abilities.values())), ("items", items)):
    json.dump(obj, open(os.path.join(HERE, f + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(pokemon)} entradas de Pokémon, {len(moves)} movimientos, {len(abilities)} habilidades, {len(items)} objetos")
print("Movimientos descartados (no existen en Showdown):", sorted(dropped))
