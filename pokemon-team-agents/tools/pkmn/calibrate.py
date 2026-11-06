"""Calibración del surrogate con la simulación.

Ajusta (regresión ridge sobre componentes estandarizados) cuánto pesa cada componente del desglose
para predecir el winrate simulado. Así la proporción cobertura/potencia/roles NO la fija un humano
a ojo: la dictan las partidas. Se sugiere, no se aplica: el arquitecto decide y lo documenta.
"""
from __future__ import annotations

import math

COMPONENTS = ("defensa_tipos", "amenazas", "presion_ofensiva", "roles", "velocidad", "calidad_individual")


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = _rank(a), _rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return round(cov / (va * vb), 3) if va and vb else 0.0


def _solve(A, b):
    """Gauss-Jordan para sistemas pequeños."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            continue
        piv = M[c][c]
        M[c] = [v / piv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]


def calibrate(rows, weights, ridge: float = 1.0) -> dict:
    """rows: [(breakdown, winrate)]. Devuelve informe con pesos sugeridos."""
    X = [[br[k] for k in COMPONENTS] for br, _ in rows]
    y = [wr for _, wr in rows]
    n, k = len(X), len(COMPONENTS)
    mu = [sum(r[j] for r in X) / n for j in range(k)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / n) or 1.0 for j in range(k)]
    Z = [[(r[j] - mu[j]) / sd[j] for j in range(k)] for r in X]
    ym = sum(y) / n
    A = [[sum(Z[i][a] * Z[i][b] for i in range(n)) + (ridge if a == b else 0) for b in range(k)] for a in range(k)]
    bvec = [sum(Z[i][a] * (y[i] - ym) for i in range(n)) for a in range(k)]
    beta = _solve(A, bvec)
    raw = [beta[j] / sd[j] for j in range(k)]  # peso en unidades originales
    pos = [max(0.05, r) for r in raw]  # nunca negativo: un componente no puede "restar" por sí mismo
    scale = sum(weights[c] for c in COMPONENTS) / sum(pos)
    sugg = {c: round(v * scale, 3) for c, v in zip(COMPONENTS, pos)}
    cur_total = [sum(br[c] * weights[c] for c in COMPONENTS) - br.get("penalizacion", 0) for br, _ in rows]
    new_total = [sum(br[c] * sugg[c] for c in COMPONENTS) - br.get("penalizacion", 0) for br, _ in rows]
    return {
        "n_equipos": n,
        "spearman_actual": spearman(cur_total, y),
        "spearman_calibrado": spearman(new_total, y),
        "coeficientes_estandarizados": {c: round(b, 4) for c, b in zip(COMPONENTS, beta)},
        "pesos_actuales": {c: weights[c] for c in COMPONENTS},
        "pesos_sugeridos": sugg,
        "nota": ("Si spearman_calibrado > spearman_actual + 0.1 con >= 25 equipos, copia pesos_sugeridos a "
                 "config/pesos_equipo.json y repite la búsqueda (equipo). Con pocos equipos la calibración es ruidosa y spearman_calibrado se mide dentro de muestra (optimista)."),
    }
