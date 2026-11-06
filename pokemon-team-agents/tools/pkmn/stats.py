"""Cálculo de stats. Reglas de la partida: nivel 49 y EVs = 0 (configurable en config/reglas.json)."""
from __future__ import annotations

import math

STATS = ["hp", "atk", "def", "spa", "spd", "spe"]

# naturaleza -> (stat que sube, stat que baja); None = neutra
NATURES = {
    "Hardy": (None, None), "Lonely": ("atk", "def"), "Brave": ("atk", "spe"), "Adamant": ("atk", "spa"),
    "Naughty": ("atk", "spd"), "Bold": ("def", "atk"), "Docile": (None, None), "Relaxed": ("def", "spe"),
    "Impish": ("def", "spa"), "Lax": ("def", "spd"), "Timid": ("spe", "atk"), "Hasty": ("spe", "def"),
    "Serious": (None, None), "Jolly": ("spe", "spa"), "Naive": ("spe", "spd"), "Modest": ("spa", "atk"),
    "Mild": ("spa", "def"), "Quiet": ("spa", "spe"), "Bashful": (None, None), "Rash": ("spa", "spd"),
    "Calm": ("spd", "atk"), "Gentle": ("spd", "def"), "Sassy": ("spd", "spe"), "Careful": ("spd", "spa"),
    "Quirky": (None, None),
}

NATURES_ES = {
    "fuerte": "Hardy", "huraña": "Lonely", "audaz": "Brave", "firme": "Adamant", "pícara": "Naughty",
    "picara": "Naughty", "osada": "Bold", "dócil": "Docile", "docil": "Docile", "plácida": "Relaxed",
    "placida": "Relaxed", "agitada": "Impish", "floja": "Lax", "miedosa": "Timid", "activa": "Hasty",
    "seria": "Serious", "alegre": "Jolly", "ingenua": "Naive", "modesta": "Modest", "afable": "Mild",
    "mansa": "Quiet", "tímida": "Bashful", "timida": "Bashful", "alocada": "Rash", "serena": "Calm",
    "amable": "Gentle", "grosera": "Sassy", "cauta": "Careful", "rara": "Quirky",
}


def norm_nature(n: str | None) -> str:
    if not n:
        return "Serious"
    if n in NATURES:
        return n
    k = n.strip().lower()
    if k in NATURES_ES:
        return NATURES_ES[k]
    for x in NATURES:
        if x.lower() == k:
            return x
    raise ValueError(f"Naturaleza desconocida: {n!r}")


def nature_mult(nature: str, stat: str) -> float:
    up, down = NATURES[norm_nature(nature)]
    if stat == up:
        return 1.1
    if stat == down:
        return 0.9
    return 1.0


def calc_stat(stat: str, base: int, level: int, iv: int = 31, ev: int = 0, nature: str = "Serious") -> int:
    core = math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100)
    if stat == "hp":
        if base == 1:  # Shedinja
            return 1
        return core + level + 10
    return math.floor((core + 5) * nature_mult(nature, stat))


def calc_all(base_stats: dict, level: int, ivs: dict | None = None, evs: dict | None = None,
             nature: str = "Serious") -> dict:
    ivs = ivs or {}
    evs = evs or {}
    return {s: calc_stat(s, base_stats[s], level, ivs.get(s, 31), evs.get(s, 0), nature) for s in STATS}


STAGE_MULT = {i: (max(2, 2 + i) / max(2, 2 - i)) for i in range(-6, 7)}


def apply_stage(value: int, stage: int) -> int:
    return math.floor(value * STAGE_MULT[max(-6, min(6, stage))])


def best_natures_for_role(role: str) -> list[str]:
    """Sugerencias por rol (sube lo que importa, baja el ataque que no usas)."""
    return {
        "physical_attacker": ["Adamant", "Jolly"],
        "special_attacker": ["Modest", "Timid"],
        "mixed_attacker": ["Lonely", "Mild", "Naive", "Hasty", "Rash", "Naughty"],
        "physical_wall": ["Bold", "Impish", "Relaxed"],
        "special_wall": ["Calm", "Careful", "Sassy"],
        "support": ["Bold", "Calm", "Impish", "Careful", "Timid", "Jolly"],
        "trick_room": ["Brave", "Quiet", "Relaxed", "Sassy"],
    }.get(role, ["Serious"])
