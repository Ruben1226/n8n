"""Tabla de tipos (Gen 6+, con Hada). Claves internas en inglés; acepta nombres en español.

Si Pokémon Añil modifica la tabla, edita config/tabla_tipos_override.json:
  {"Fire": {"Fairy": 2.0}}   -> Fuego pasa a ser súper eficaz contra Hada.
"""
from __future__ import annotations

import json
import os
from itertools import combinations

TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", "Ground",
    "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
]

ES_TO_EN = {
    "normal": "Normal", "fuego": "Fire", "agua": "Water", "electrico": "Electric", "eléctrico": "Electric",
    "planta": "Grass", "hielo": "Ice", "lucha": "Fighting", "veneno": "Poison", "tierra": "Ground",
    "volador": "Flying", "psiquico": "Psychic", "psíquico": "Psychic", "bicho": "Bug", "roca": "Rock",
    "fantasma": "Ghost", "dragon": "Dragon", "dragón": "Dragon", "siniestro": "Dark", "acero": "Steel",
    "hada": "Fairy",
}

# atacante -> {defensor: multiplicador}; lo que no aparece vale 1
_SE = {
    "Fire": ["Grass", "Ice", "Bug", "Steel"],
    "Water": ["Fire", "Ground", "Rock"],
    "Electric": ["Water", "Flying"],
    "Grass": ["Water", "Ground", "Rock"],
    "Ice": ["Grass", "Ground", "Flying", "Dragon"],
    "Fighting": ["Normal", "Ice", "Rock", "Dark", "Steel"],
    "Poison": ["Grass", "Fairy"],
    "Ground": ["Fire", "Electric", "Poison", "Rock", "Steel"],
    "Flying": ["Grass", "Fighting", "Bug"],
    "Psychic": ["Fighting", "Poison"],
    "Bug": ["Grass", "Psychic", "Dark"],
    "Rock": ["Fire", "Ice", "Flying", "Bug"],
    "Ghost": ["Psychic", "Ghost"],
    "Dragon": ["Dragon"],
    "Dark": ["Psychic", "Ghost"],
    "Steel": ["Ice", "Rock", "Fairy"],
    "Fairy": ["Fighting", "Dragon", "Dark"],
}
_NVE = {
    "Normal": ["Rock", "Steel"],
    "Fire": ["Fire", "Water", "Rock", "Dragon"],
    "Water": ["Water", "Grass", "Dragon"],
    "Electric": ["Electric", "Grass", "Dragon"],
    "Grass": ["Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"],
    "Ice": ["Fire", "Water", "Ice", "Steel"],
    "Fighting": ["Poison", "Flying", "Psychic", "Bug", "Fairy"],
    "Poison": ["Poison", "Ground", "Rock", "Ghost"],
    "Ground": ["Grass", "Bug"],
    "Flying": ["Electric", "Rock", "Steel"],
    "Psychic": ["Psychic", "Steel"],
    "Bug": ["Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel", "Fairy"],
    "Rock": ["Fighting", "Ground", "Steel"],
    "Ghost": ["Dark"],
    "Dragon": ["Steel"],
    "Dark": ["Fighting", "Dark", "Fairy"],
    "Steel": ["Fire", "Water", "Electric", "Steel"],
    "Fairy": ["Fire", "Poison", "Steel"],
}
_IMMUNE = {
    "Normal": ["Ghost"], "Ghost": ["Normal"], "Electric": ["Ground"], "Ground": ["Flying"],
    "Fighting": ["Ghost"], "Poison": ["Steel"], "Psychic": ["Dark"], "Dragon": ["Fairy"],
}


def _build() -> dict:
    chart = {a: {d: 1.0 for d in TYPES} for a in TYPES}
    for a, ds in _SE.items():
        for d in ds:
            chart[a][d] = 2.0
    for a, ds in _NVE.items():
        for d in ds:
            chart[a][d] = 0.5
    for a, ds in _IMMUNE.items():
        for d in ds:
            chart[a][d] = 0.0
    # Modo Inverso de Añil (config/reglas.json -> "modo_inverso": true): x2 <-> x0.5 y las inmunidades pasan a x2
    reglas = os.path.join(os.path.dirname(__file__), "..", "..", "config", "reglas.json")
    if os.path.exists(reglas):
        with open(reglas, encoding="utf-8") as f:
            if json.load(f).get("modo_inverso"):
                for a in TYPES:
                    for d in TYPES:
                        m = chart[a][d]
                        chart[a][d] = 0.5 if m == 2.0 else 2.0 if m in (0.5, 0.0) else m
    override = os.path.join(os.path.dirname(__file__), "..", "..", "config", "tabla_tipos_override.json")
    if os.path.exists(override):
        with open(override, encoding="utf-8") as f:
            for a, row in json.load(f).items():
                if a.startswith("_"):
                    continue
                for d, m in row.items():
                    chart[norm_type(a)][norm_type(d)] = float(m)
    return chart


def norm_type(t: str) -> str:
    if t in TYPES:
        return t
    key = t.strip().lower()
    if key in ES_TO_EN:
        return ES_TO_EN[key]
    for x in TYPES:
        if x.lower() == key:
            return x
    raise ValueError(f"Tipo desconocido: {t!r}")


CHART = _build()


def effectiveness(atk_type: str, def_types: list[str]) -> float:
    atk_type = norm_type(atk_type)
    m = 1.0
    for d in def_types:
        m *= CHART[atk_type][norm_type(d)]
    return m


def all_type_combos() -> list[tuple[str, ...]]:
    """Las 18 monotipos + 153 combinaciones dobles."""
    return [(t,) for t in TYPES] + list(combinations(TYPES, 2))


def defensive_profile(def_types: list[str]) -> dict[str, float]:
    return {a: effectiveness(a, def_types) for a in TYPES}
