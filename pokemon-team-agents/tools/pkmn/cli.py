"""CLI del motor. Ejecutar desde la raíz del proyecto:

  python -m tools.pkmn.cli validar                     # integridad de workspace/01_datos
  python -m tools.pkmn.cli stats Gyarados --naturaleza Firme
  python -m tools.pkmn.cli calc sets.json idA idB      # o: calc-rapido (ver --help)
  python -m tools.pkmn.cli sets                        # -> workspace/03_sets/sets_candidatos.json
  python -m tools.pkmn.cli amenazas                    # -> workspace/04_amenazas/{amenazas,matriz}.json
  python -m tools.pkmn.cli equipo [--fijar Especie ...] # -> workspace/05_equipos/top_equipos.json
  python -m tools.pkmn.cli evaluar id1 id2 id3 id4 id5 id6
  python -m tools.pkmn.cli exportar workspace/05_equipos/top_equipos.json 0

Opción global: --datos DIR (por defecto workspace/01_datos)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .data import Dex, ROOT, key
from .damage import battler_from_set, calc, effective_speed
from .setgen import generate_all
from .stats import calc_all, norm_nature
from .teamsearch import evaluate, load_weights, search, to_showdown
from .threats import build_matrix, generic_threats, pool_threats

WS = os.path.join(ROOT, "workspace")


def _dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"-> {os.path.relpath(path, ROOT)}")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _rules_with_stock(dex: Dex) -> dict:
    r = dict(dex.rules)
    r["_stock_objetos"] = {key(i["name"]): i.get("quantity", 99) for i in dex.available_items()}
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pkmn")
    ap.add_argument("--datos", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validar")
    p = sub.add_parser("stats"); p.add_argument("especie"); p.add_argument("--naturaleza", default=None)
    p = sub.add_parser("calc", help="calc entre dos sets de un fichero JSON de sets")
    p.add_argument("fichero"); p.add_argument("atacante"); p.add_argument("defensor")
    p.add_argument("--clima", default=None); p.add_argument("--critico", action="store_true")
    p.add_argument("--etapas-atq", type=int, default=0)
    sub.add_parser("sets")
    p = sub.add_parser("amenazas"); p.add_argument("--n-pool", type=int, default=30)
    p.add_argument("--max-candidatos", type=int, default=400)
    p = sub.add_parser("equipo"); p.add_argument("--fijar", nargs="*", default=[])
    p.add_argument("--generaciones", type=int, default=150); p.add_argument("--poblacion", type=int, default=200)
    p.add_argument("--semilla", type=int, default=7)
    p = sub.add_parser("evaluar"); p.add_argument("ids", nargs=6)
    p = sub.add_parser("exportar"); p.add_argument("fichero"); p.add_argument("indice", type=int, nargs="?", default=0)
    a = ap.parse_args(argv)

    dex = Dex(a.datos)

    if a.cmd == "validar":
        probs = dex.validate()
        print(f"{len(dex.pokemon)} Pokémon, {len({id(v) for v in dex.moves.values()})} movimientos, "
              f"{len({id(v) for v in dex.abilities.values()})} habilidades, {len({id(v) for v in dex.items.values()})} objetos")
        print("\n".join(probs) if probs else "OK: sin problemas")
        return 1 if probs else 0

    if a.cmd == "stats":
        sp = dex.species(a.especie)
        nat = norm_nature(a.naturaleza or sp.get("nature"))
        print(nat, calc_all(sp["base_stats"], dex.rules.get("nivel", 49), sp.get("ivs", {}), {}, nat))
        return 0

    if a.cmd == "calc":
        sets = {s["id"]: s for s in (_load(a.fichero) if not a.fichero.endswith("top_equipos.json") else [])}
        A, D = battler_from_set(dex, sets[a.atacante]), battler_from_set(dex, sets[a.defensor])
        A.stages = {"atk": a.etapas_atq, "spa": a.etapas_atq}
        fld = {"weather": a.clima}
        print(f"Velocidad: {A.name} {effective_speed(A, fld)} vs {D.name} {effective_speed(D, fld)}")
        for m in A.moves:
            md = dex.move(m)
            if md and md["category"] != "status":
                r = calc(A, D, md, fld, crit=a.critico)
                print(f"  {m:<22} {r['min_pct']:>5}% - {r['max_pct']:>5}%  ({r['hits_to_ko'][0]}-{r['hits_to_ko'][1]}HKO) x{r['eff']}")
        return 0

    if a.cmd == "sets":
        sets, thr = generate_all(dex)
        _dump(sets, os.path.join(WS, "03_sets", "sets_candidatos.json"))
        print(f"{len(sets)} sets generados; umbral de 'rápido' = {thr} de velocidad")
        return 0

    if a.cmd == "amenazas":
        sets = _load(os.path.join(WS, "03_sets", "sets_candidatos.json"))
        rev = os.path.join(WS, "03_sets", "sets_revisados.json")
        if os.path.exists(rev):
            sets = _load(rev); print("Usando sets_revisados.json")
        extra_p = os.path.join(WS, "04_amenazas", "amenazas_extra.json")
        threats = pool_threats(sets, a.n_pool) + generic_threats() + (_load(extra_p) if os.path.exists(extra_p) else [])
        cands = sorted(sets, key=lambda s: s["scores"]["total"], reverse=True)[: a.max_candidatos]
        _dump(threats, os.path.join(WS, "04_amenazas", "amenazas.json"))
        _dump(build_matrix(dex, cands, threats), os.path.join(WS, "04_amenazas", "matriz.json"))
        _dump([c["id"] for c in cands], os.path.join(WS, "04_amenazas", "candidatos_en_matriz.json"))
        return 0

    if a.cmd in ("equipo", "evaluar"):
        rev = os.path.join(WS, "03_sets", "sets_revisados.json")
        sets = _load(rev if os.path.exists(rev) else os.path.join(WS, "03_sets", "sets_candidatos.json"))
        ids = set(_load(os.path.join(WS, "04_amenazas", "candidatos_en_matriz.json")))
        cands = [s for s in sets if s["id"] in ids]
        matrix = _load(os.path.join(WS, "04_amenazas", "matriz.json"))
        threats = _load(os.path.join(WS, "04_amenazas", "amenazas.json"))
        rules = _rules_with_stock(dex)
        if a.cmd == "evaluar":
            by = {s["id"]: s for s in cands}
            print(json.dumps(evaluate([by[i] for i in a.ids], matrix, threats, rules, load_weights()), ensure_ascii=False, indent=1))
            return 0
        res = search(cands, matrix, threats, rules, pop=a.poblacion, gens=a.generaciones, seed=a.semilla, locked=a.fijar)
        _dump(res, os.path.join(WS, "05_equipos", "top_equipos.json"))
        for i, r in enumerate(res[:5]):
            print(f"#{i} total={r['breakdown']['total']}  " + ", ".join(s.split('|')[0] for s in r["team"]))
        return 0

    if a.cmd == "exportar":
        res = _load(a.fichero)
        print("\n\n".join(to_showdown(s) for s in res[a.indice]["sets"]))
        return 0


if __name__ == "__main__":
    sys.exit(main())
