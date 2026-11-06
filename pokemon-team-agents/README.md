# Pokémon Añil · Sistema de agentes para el mejor equipo competitivo

Partida **random**, singles 6 contra 6, **nivel 49**, **0 EVs**, naturalezas con mentas limitadas, sin Homenaje Póstumo, cláusula de sueño y boosts ilimitados.

## Qué hay aquí
```
CLAUDE.md                  ← instrucciones del ORQUESTADOR (Claude Code las carga solo)
.claude/agents/            ← 8 subagentes especializados
.claude/commands/          ← /construir-equipo: lanza todo el pipeline
knowledge/                 ← base de conocimiento: reglas, fórmulas, tipos, movimientos, habilidades,
                             objetos, estados/clima/hazards, roles, metodología, nivel 49, glosario ES↔EN
config/                    ← reglas de la partida, pesos del optimizador, efectos estándar, override de tipos
schemas/                   ← formato JSON de los datos normalizados
tools/pkmn/                ← MOTOR determinista en Python (solo librería estándar)
tests/                     ← tests del motor (fórmula de daño validada con Bulbapedia)
data/ejemplo/              ← mini dataset de 10 Pokémon para probar
data/entrada/              ← AQUÍ va tu fichero de la partida
workspace/                 ← salidas de cada fase (se rellena al ejecutar)
```

## Los agentes
| # | Agente | Hace | Herramienta clave |
|---|---|---|---|
| 1 | `ingestor-datos` | Fichero bruto → JSON normalizado y validado | `cli validar` |
| 2 | `oraculo-mecanicas` | Codifica efectos de habilidades/objetos (incluidos los de Añil); ranking de habilidades | vocabulario de efectos |
| 3 | `evaluador-individual` | 2–4 mejores sets por Pokémon; ranking; joyas y trampas | `cli sets`, `cli calc` |
| 4 | `analista-amenazas` | "Meta sintético": lo mejor del pool + arquetipos por tipo + amenazas conceptuales; matriz de enfrentamientos | `cli amenazas` |
| 5 | `arquitecto-equipo` | Algoritmo genético + criterio experto → 3–5 equipos candidatos | `cli equipo`, `cli evaluar` |
| 6 | `asesor-naturalezas` | Asigna las mentas por ganancia marginal | matriz + calc |
| 7 | `critico-red-team` | Diseña los peores rivales, simula y propone cambios (en bucle) | calc + matriz |
| 8 | `estratega-informe` | Informe final: export de Showdown, plan de juego, velocidades, cálculos clave | `cli exportar` |

**Principio:** los LLM razonan y el motor calcula. Ningún número de daño o velocidad sale "a ojo".

## Cómo usarlo
1. Necesitas **Claude Code** y **Python 3.10+** (sin dependencias externas).
2. Descomprime y abre la carpeta con Claude Code: `cd pokemon-team-agents && claude`.
3. Rellena `config/reglas.json`: **mentas disponibles**, MTs que tienes, si puedes cambiar habilidades…
4. Copia tu fichero en `data/entrada/`.
5. Escribe `/construir-equipo`. Opcional: `/construir-equipo quiero a Gyarados sí o sí`.

### Probar el motor sin tu fichero
```bash
python -m unittest discover -s tests -v
python -m tools.pkmn.cli --datos data/ejemplo validar
python -m tools.pkmn.cli --datos data/ejemplo sets
python -m tools.pkmn.cli --datos data/ejemplo amenazas
python -m tools.pkmn.cli --datos data/ejemplo equipo --generaciones 60
python -m tools.pkmn.cli --datos data/ejemplo exportar workspace/05_equipos/top_equipos.json 0
```

## Limitaciones conocidas del motor (los agentes las compensan con juicio)
- **No simula partidas completas.** Evalúa enfrentamientos 1 contra 1, cobertura, roles y velocidad. Una posible mejora futura es un mod de Pokémon Showdown con los datos de Añil, para simular miles de combates.
- Habilidades y objetos no calculables (Regeneración, Bromista, Restos…) se tratan como `note`.
- Los multigolpe asumen 3 golpes (5 con Encadenado). Los críticos y la precisión se tratan como valor esperado.
- Los hazards, el clima y las pantallas no entran en la matriz automática; el crítico y el estratega los razonan.
