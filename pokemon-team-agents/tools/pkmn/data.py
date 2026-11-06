"""Carga de datos normalizados (salida del agente ingestor) y reglas de la partida.

Ficheros esperados en el directorio de datos (por defecto workspace/01_datos):
  pokemon.json, moves.json, abilities.json, items.json
Ver schemas/ para el formato exacto.
"""
from __future__ import annotations

import json
import os
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATA_DIR = os.path.join(ROOT, "workspace", "01_datos")


def key(name: str) -> str:
    """Clave canónica: minúsculas, sin acentos, sin espacios ni guiones."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c for c in n.lower() if c.isalnum())


def _load(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_rules(path: str | None = None) -> dict:
    return _load(path or os.path.join(ROOT, "config", "reglas.json"), {})


class Dex:
    def __init__(self, data_dir: str | None = None, rules: dict | None = None):
        d = data_dir or DEFAULT_DATA_DIR
        self.rules = rules if rules is not None else load_rules()
        self.pokemon = _load(os.path.join(d, "pokemon.json"), [])
        self.moves = {key(m["name"]): m for m in _load(os.path.join(d, "moves.json"), [])}
        self.abilities = {key(a["name"]): a for a in _load(os.path.join(d, "abilities.json"), [])}
        self.items = {key(i["name"]): i for i in _load(os.path.join(d, "items.json"), [])}
        std = _load(os.path.join(ROOT, "config", "efectos_estandar.json"), {})
        self._std_abilities = {key(k): v for k, v in std.get("abilities", {}).items()}
        self._std_items = {key(k): v for k, v in std.get("items", {}).items()}
        # alias en español -> nombre canónico
        for table in (self.moves, self.abilities, self.items):
            for entry in list(table.values()):
                for alias in entry.get("aliases", []) + ([entry["name_es"]] if entry.get("name_es") else []):
                    table.setdefault(key(alias), entry)

    # ---------- búsquedas ----------
    def move(self, name: str) -> dict | None:
        return self.moves.get(key(name))

    def ability_effects(self, name: str | None) -> list[dict]:
        if not name:
            return []
        a = self.abilities.get(key(name))
        if a and a.get("effects") is not None:
            return a["effects"]
        return self._std_abilities.get(key(name), [])

    def item_effects(self, name: str | None) -> list[dict]:
        if not name:
            return []
        i = self.items.get(key(name))
        if i and i.get("effects") is not None:
            return i["effects"]
        return self._std_items.get(key(name), [])

    def species(self, name: str) -> dict | None:
        k = key(name)
        for p in self.pokemon:
            if key(p.get("id", p["name"])) == k or key(p["name"]) == k:
                return p
        return None

    # ---------- legalidad ----------
    def legal_moves(self, mon: dict) -> list[str]:
        r = self.rules
        level = r.get("nivel", 49)
        banned = {key(m) for m in r.get("movimientos_prohibidos", [])}
        ls = mon.get("learnset", {})
        out: list[str] = []
        for e in ls.get("level_up", []):
            lvl = e.get("level", 1) if isinstance(e, dict) else 1
            name = e["move"] if isinstance(e, dict) else e
            if lvl <= level:
                out.append(name)
        out += ls.get("relearn", [])
        tms_ok = r.get("mts_disponibles", "all")
        for m in ls.get("tm", []):
            if tms_ok == "all" or key(m) in {key(x) for x in tms_ok}:
                out.append(m)
        if r.get("tutores_disponibles", True):
            out += ls.get("tutor", [])
        if r.get("movimientos_huevo", False):
            out += ls.get("egg", [])
        out += mon.get("current_moves", [])
        seen, res = set(), []
        for m in out:
            k = key(m)
            if k in seen or k in banned:
                continue
            seen.add(k)
            res.append(m)
        return res

    def available_items(self) -> list[dict]:
        """Objetos que el jugador tiene (quantity > 0 o sin cantidad = ilimitado)."""
        return [i for i in {id(v): v for v in self.items.values()}.values() if i.get("quantity", 1) != 0]

    def validate(self) -> list[str]:
        """Devuelve una lista de problemas de integridad de datos."""
        problems = []
        for p in self.pokemon:
            for s in ("hp", "atk", "def", "spa", "spd", "spe"):
                if s not in p.get("base_stats", {}):
                    problems.append(f"{p['name']}: falta stat base '{s}'")
            if not 1 <= len(p.get("types", [])) <= 2:
                problems.append(f"{p['name']}: número de tipos inválido")
            if not 1 <= len(p.get("abilities", [])) <= 3:
                problems.append(f"{p['name']}: debe tener 1-3 habilidades")
            for m in self.legal_moves(p):
                if not self.move(m):
                    problems.append(f"{p['name']}: movimiento '{m}' no está en moves.json")
            for a in p.get("abilities", []):
                if key(a) not in self.abilities and key(a) not in self._std_abilities:
                    problems.append(f"{p['name']}: habilidad '{a}' sin definición de efectos")
        for m in {id(v): v for v in self.moves.values()}.values():
            if m.get("category") not in ("physical", "special", "status"):
                problems.append(f"Movimiento {m['name']}: categoría inválida")
        return problems
