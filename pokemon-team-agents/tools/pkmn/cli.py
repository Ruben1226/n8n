"""CLI del motor. Ejecutar desde la raíz del proyecto:

  python -m tools.pkmn.cli validar                     # integridad de workspace/01_datos
  python -m tools.pkmn.cli stats Gyarados --naturaleza Firme
  python -m tools.pkmn.cli calc sets.json idA idB      # o: calc-rapido (ver --help)
  python -m tools.pkmn.cli sets                        # -> workspace/03_sets/sets_candidatos.json
  python -m tools.pkmn.cli puntuar [fichero]           # re-puntúa sets editados (por defecto sets_revisados.json)
  python -m tools.pkmn.cli amenazas                    # -> workspace/04_amenazas/{amenazas,matriz}.json
  python -m tools.pkmn.cli equipo [--fijar Especie ...] # -> workspace/05_equipos/top_equipos.json
  python -m tools.pkmn.cli evaluar id1 id2 id3 id4 id5 id6
  python -m tools.pkmn.cli exportar workspace/05_equipos/top_equipos.json 0
  python -m tools.pkmn.cli refinar [--indice 0] [--rondas 3] [--por-hueco 2]   # mejora local por simulación
  python -m tools.pkmn.cli calibrar [--top 15] [--aleatorios 15]   # ajusta pesos del surrogate con la simulación
  python -m tools.pkmn.cli simular [--top 8] [--n 4] [--random-rivales 30] [--rivales-pool 20] [--extra fichero.json]

Opción global: --datos DIR (por defecto workspace/01_datos)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .data import Dex, ROOT, key
from .damage import battler_from_set, calc, effective_speed
from .setgen import generate_all, rescore_all
from .stats import calc_all, norm_nature
from .teamsearch import evaluate, load_weights, quality_floor_of, search, to_showdown
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


def _load_sets():
    rev = os.path.join(WS, "03_sets", "sets_revisados.json")
    return _load(rev if os.path.exists(rev) else os.path.join(WS, "03_sets", "sets_candidatos.json"))


def _team_name(i, sets):
    return f"top{i}_" + "-".join(s["species"][:6] for s in sets)


def _build_rivals(sets, equipos, n_pool, seed):
    """Rivales fijos: los candidatos (round-robin) + equipos razonables muestreados del propio pool.
    Se guardan en workspace/07_sim/rivales.json para reutilizarlos (comparaciones justas)."""
    import random as _r
    rng = _r.Random(seed)
    good = sorted(sets, key=lambda s: s["scores"]["total"], reverse=True)
    good = good[: max(12, int(len(good) * 0.6))]
    by_sp = {}
    for s_ in good:
        by_sp.setdefault(s_.get("species_key", s_["species"]), []).append(s_)
    rivales = [dict(e, nombre="riv_" + e["nombre"]) for e in equipos]
    for i in range(n_pool):
        if len(by_sp) < 6:
            break
        sp = rng.sample(list(by_sp), 6)
        rivales.append({"nombre": f"pool_{i}", "sets": [rng.choice(by_sp[x][:3]) for x in sp]})
    return rivales


def _run_sim(equipos, rivales, d, datos, a, tag="sim"):
    """Lanza sim/simular.js repartiendo los equipos entre varios procesos (1 por núcleo) y fusiona resultados."""
    import subprocess
    os.makedirs(d, exist_ok=True)
    fr = os.path.join(d, f"{tag}_rivales.json")
    _dump(rivales, fr)
    k = max(1, min(len(equipos), getattr(a, "procesos", 0) or (os.cpu_count() or 2)))
    chunks = [equipos[i::k] for i in range(k)]
    procs = []
    for i, ch in enumerate(chunks):
        fe, fo = os.path.join(d, f"{tag}_equipos_{i}.json"), os.path.join(d, f"{tag}_resultados_{i}.json")
        with open(fe, "w", encoding="utf-8") as f:
            json.dump(ch, f, ensure_ascii=False)
        cmd = ["node", os.path.join(ROOT, "sim", "simular.js"), "--equipos", fe, "--rivales", fr,
               "--random-rivales", str(a.random_rivales), "--n", str(a.n), "--datos", datos,
               "--logs", os.path.join(d, "logs", tag), "--out", fo, "--semilla", str(a.semilla)]
        procs.append((subprocess.Popen(cmd, stdout=subprocess.DEVNULL), fe, fo))
    merged = None
    for pr, fe, fo in procs:
        if pr.wait() != 0:
            return 1, None
        r = _load(fo)
        os.remove(fe); os.remove(fo)
        if merged is None:
            merged = r
        else:
            merged["resultados"] += r["resultados"]
            merged["avisos"] = sorted(set(merged["avisos"]) | set(r["avisos"]))
    merged["resultados"].sort(key=lambda r: r["winrate"], reverse=True)
    _dump(merged, os.path.join(d, f"{tag}_resultados.json"))
    for r in merged["resultados"]:
        print(f"{r['winrate']:.3f}  [{r['ic95'][0]:.3f}-{r['ic95'][1]:.3f}]  vs_random={r['winrate_vs_random']}  vs_pool={r['winrate_vs_pool']}  {r['nombre']}")
    if merged["avisos"]:
        print("AVISOS:\n" + "\n".join(merged["avisos"]))
    return 0, merged


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
    p = sub.add_parser("puntuar", help="recalcula puntuaciones/percentiles de un fichero de sets editado a mano")
    p.add_argument("fichero", nargs="?", default=None)
    p = sub.add_parser("amenazas"); p.add_argument("--n-pool", type=int, default=30)
    p.add_argument("--max-candidatos", type=int, default=400)
    p = sub.add_parser("equipo"); p.add_argument("--fijar", nargs="*", default=[])
    p.add_argument("--generaciones", type=int, default=150); p.add_argument("--poblacion", type=int, default=200)
    p.add_argument("--semilla", type=int, default=7)
    p = sub.add_parser("evaluar"); p.add_argument("ids", nargs=6)
    p = sub.add_parser("simular", help="valida por simulación (Node + Showdown) los mejores equipos")
    p.add_argument("--top", type=int, default=8); p.add_argument("--n", type=int, default=4)
    p.add_argument("--random-rivales", type=int, default=30); p.add_argument("--rivales-pool", type=int, default=20)
    p.add_argument("--extra", default=None, help="JSON con equipos adicionales a evaluar [{nombre, sets}]")
    p.add_argument("--semilla", type=int, default=1)
    p.add_argument("--procesos", type=int, default=0, help="0 = un proceso por núcleo")
    p = sub.add_parser("refinar", help="búsqueda local guiada por simulación sobre un equipo de top_equipos")
    p.add_argument("--indice", type=int, default=0); p.add_argument("--n", type=int, default=4)
    p.add_argument("--desde", default=None, help="JSON con el equipo a refinar ({sets:[...]} o lista de sets); si no, usa top_equipos[indice]")
    p.add_argument("--random-rivales", type=int, default=30); p.add_argument("--rivales-pool", type=int, default=20)
    p.add_argument("--por-hueco", type=int, default=2); p.add_argument("--rondas", type=int, default=3)
    p.add_argument("--margen", type=float, default=0.02); p.add_argument("--semilla", type=int, default=1)
    p.add_argument("--procesos", type=int, default=0, help="0 = un proceso por núcleo")
    p = sub.add_parser("calibrar", help="ajusta los pesos del surrogate para que predigan el winrate simulado")
    p.add_argument("--top", type=int, default=15); p.add_argument("--aleatorios", type=int, default=15)
    p.add_argument("--n", type=int, default=4); p.add_argument("--random-rivales", type=int, default=30)
    p.add_argument("--rivales-pool", type=int, default=16); p.add_argument("--semilla", type=int, default=1)
    p.add_argument("--procesos", type=int, default=0)
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

    if a.cmd == "puntuar":
        f = a.fichero or os.path.join(WS, "03_sets", "sets_revisados.json")
        out = rescore_all(dex, _load(f))
        _dump(out, f)
        print(f"{len(out)} sets re-puntuados")
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
            w = load_weights()
            print(json.dumps(evaluate([by[i] for i in a.ids], matrix, threats, rules, w, quality_floor_of(cands, w)), ensure_ascii=False, indent=1))
            return 0
        res = search(cands, matrix, threats, rules, pop=a.poblacion, gens=a.generaciones, seed=a.semilla, locked=a.fijar)
        _dump(res, os.path.join(WS, "05_equipos", "top_equipos.json"))
        for i, r in enumerate(res[:5]):
            print(f"#{i} total={r['breakdown']['total']}  " + ", ".join(s.split('|')[0] for s in r["team"]))
        return 0

    if a.cmd in ("simular", "refinar"):
        sets = _load_sets()
        top = _load(os.path.join(WS, "05_equipos", "top_equipos.json"))
        d = os.path.join(WS, "07_sim")
        datos = a.datos or os.path.join(WS, "01_datos")
        rules = _rules_with_stock(dex)
        if a.cmd == "simular":
            equipos = [{"nombre": _team_name(i, t["sets"]), "sets": t["sets"]} for i, t in enumerate(top[: a.top])]
            rivales = _build_rivals(sets, equipos, a.rivales_pool, a.semilla)
            if a.extra:
                equipos += _load(a.extra)
            return _run_sim(equipos, rivales, d, datos, a)[0]
        # refinar: búsqueda local guiada por simulación sobre el equipo elegido
        ids = set(_load(os.path.join(WS, "04_amenazas", "candidatos_en_matriz.json")))
        cands = [s_ for s_ in sets if s_["id"] in ids]
        matrix = _load(os.path.join(WS, "04_amenazas", "matriz.json"))
        threats = _load(os.path.join(WS, "04_amenazas", "amenazas.json"))
        w = load_weights()
        qf = quality_floor_of(cands, w)
        if a.desde:
            src = _load(a.desde)
            base = src["sets"] if isinstance(src, dict) else (src[0]["sets"] if src and "sets" in src[0] else src)
            by_id = {c["id"]: c for c in sets}
            base = [by_id.get(x["id"], x) for x in base]
        else:
            base = top[a.indice]["sets"]
        rivales = _build_rivals(sets, [{"nombre": _team_name(i, t["sets"]), "sets": t["sets"]} for i, t in enumerate(top[:4])],
                                a.rivales_pool, a.semilla)
        historial = []
        for ronda in range(a.rondas):
            variantes = [{"nombre": "BASE", "sets": base}]
            used = {s_.get("species_key", s_["species"]) for s_ in base}
            for i, old in enumerate(base):
                opciones = []
                for c in cands:
                    ck, ok_ = c.get("species_key", c["species"]), old.get("species_key", old["species"])
                    if c["id"] == old["id"] or (ck in used and ck != ok_):
                        continue
                    t = base[:i] + [c] + base[i + 1:]
                    opciones.append((evaluate(t, matrix, threats, rules, w, qf)["total"], c))
                opciones.sort(key=lambda x: -x[0])
                for _, c in opciones[: a.por_hueco]:
                    variantes.append({"nombre": f"r{ronda}_{old['species'][:8]}->{c['id']}", "sets": base[:i] + [c] + base[i + 1:]})
            rc, res = _run_sim(variantes, rivales, d, datos, a, tag=f"refinar_r{ronda}")
            if rc != 0:
                return rc
            by = {r["nombre"]: r for r in res["resultados"]}
            best = max(res["resultados"], key=lambda r: r["winrate"])
            historial.append({"ronda": ronda, "base_winrate": by["BASE"]["winrate"], "mejor": best["nombre"],
                              "mejor_winrate": best["winrate"], "ic95_mejor": best["ic95"], "ic95_base": by["BASE"]["ic95"]})
            print(f"Ronda {ronda}: BASE {by['BASE']['winrate']:.3f} | mejor {best['nombre']} {best['winrate']:.3f}")
            if best["nombre"] == "BASE" or best["winrate"] < by["BASE"]["winrate"] + a.margen:
                print("Sin mejora significativa: se detiene el refinado.")
                break
            base = next(v["sets"] for v in variantes if v["nombre"] == best["nombre"])
        # Validación con rivales NUEVOS (reserva): evita el "sesgo del ganador" de elegir y medir con los mismos rivales
        validacion = None
        original = top[a.indice]["sets"] if not a.desde else None
        if a.desde:
            _src = _load(a.desde)
            original = _src["sets"] if isinstance(_src, dict) else (_src[0]["sets"] if _src and "sets" in _src[0] else _src)
        if historial and [x["id"] for x in original] != [x["id"] for x in base]:
            import copy
            a2 = copy.copy(a)
            a2.semilla = a.semilla + 997
            if a.desde:
                src = _load(a.desde)
                orig_sets = src["sets"] if isinstance(src, dict) else (src[0]["sets"] if src and "sets" in src[0] else src)
            else:
                orig_sets = original
            riv2 = _build_rivals(sets, [{"nombre": _team_name(i, t["sets"]), "sets": t["sets"]} for i, t in enumerate(top[4:8])],
                                 a.rivales_pool, a2.semilla)
            rc, res2 = _run_sim([{"nombre": "ORIGINAL", "sets": orig_sets}, {"nombre": "REFINADO", "sets": base}],
                                riv2, d, datos, a2, tag="refinar_validacion")
            if rc == 0:
                by2 = {r["nombre"]: r for r in res2["resultados"]}
                validacion = {k: {"winrate": by2[k]["winrate"], "ic95": by2[k]["ic95"]} for k in by2}
                print(f"Validación (rivales nuevos): ORIGINAL {by2['ORIGINAL']['winrate']:.3f} vs REFINADO {by2['REFINADO']['winrate']:.3f}")
        _dump({"equipo": [s_["id"] for s_ in base], "sets": base, "historial": historial, "validacion_rivales_nuevos": validacion,
               "desglose_motor": evaluate(base, matrix, threats, rules, w, qf)}, os.path.join(d, "refinado.json"))
        return 0

    if a.cmd == "calibrar":
        from .calibrate import calibrate
        sets = _load_sets()
        ids = set(_load(os.path.join(WS, "04_amenazas", "candidatos_en_matriz.json")))
        cands = [s_ for s_ in sets if s_["id"] in ids]
        matrix = _load(os.path.join(WS, "04_amenazas", "matriz.json"))
        threats = _load(os.path.join(WS, "04_amenazas", "amenazas.json"))
        top = _load(os.path.join(WS, "05_equipos", "top_equipos.json"))
        rules = _rules_with_stock(dex)
        w = load_weights()
        qf = quality_floor_of(cands, w)
        import random as _r
        rng = _r.Random(a.semilla)
        teams = [t["sets"] for t in top[: a.top]]
        by_sp = {}
        for c in cands:
            by_sp.setdefault(c.get("species_key", c["species"]), []).append(c)
        for _ in range(a.aleatorios):
            if len(by_sp) < 6:
                break
            teams.append([rng.choice(by_sp[x]) for x in rng.sample(list(by_sp), 6)])
        equipos = [{"nombre": f"cal{i}", "sets": t} for i, t in enumerate(teams)]
        rivales = _build_rivals(sets, equipos[:4], a.rivales_pool, a.semilla)
        d = os.path.join(WS, "07_sim")
        rc, res = _run_sim(equipos, rivales, d, a.datos or os.path.join(WS, "01_datos"), a, tag="calibrar")
        if rc != 0:
            return rc
        wr = {r["nombre"]: r["winrate"] for r in res["resultados"]}
        rows = [(evaluate(t, matrix, threats, rules, w, qf), wr[f"cal{i}"]) for i, t in enumerate(teams)]
        rep = calibrate(rows, w)
        _dump(rep, os.path.join(ROOT, "config", "pesos_equipo_calibrados.json"))
        print(json.dumps({k: rep[k] for k in ("spearman_actual", "spearman_calibrado", "pesos_sugeridos", "nota")}, ensure_ascii=False, indent=1))
        return 0

    if a.cmd == "exportar":
        res = _load(a.fichero)
        print("\n\n".join(to_showdown(s) for s in res[a.indice]["sets"]))
        return 0


if __name__ == "__main__":
    sys.exit(main())
