# Pokémon Añil · Sistema de agentes para el mejor equipo competitivo

Partida **random**, singles 6 contra 6, **nivel 49**, **0 EVs**, naturalezas con mentas limitadas, sin Homenaje Póstumo, cláusula de sueño y boosts ilimitados. Rivales: amigos con sus propias partidas random (sin meta).

> **Filosofía:** no existe el equipo perfecto. El sistema maximiza la **probabilidad de ganar**, no la cobertura teórica. Un "botón" que arrasa puede valer más que cubrir un tipo, y no se meten Pokémon flojos para tapar huecos (`knowledge/13`).

## Cómo decide el sistema (3 capas)
```
 1. MOTOR RÁPIDO (Python)      → explora miles de equipos en segundos (algoritmo genético)
        │                         cobertura, amenazas, presión ofensiva, roles, velocidad, eslabón débil
 2. SIMULADOR (Showdown, Node) → juega cientos de partidas reales a los finalistas
        │                         motor oficial de combate + calculadora oficial + bot heurístico
        │                         rivales: tu propio pool + equipos "random de otro jugador"
        │                         refinado hueco a hueco guiado por winrate
        │                         calibración: el motor rápido aprende qué predice las victorias
 3. AGENTES (Claude Code)      → interpretan los datos, codifican efectos de Añil, detectan combos,
                                 critican leyendo las partidas perdidas y redactan el plan de juego
```
Es el mismo esquema que usó un sistema de investigación que llegó al top 33 mundial en Showdown: algoritmo genético, fitness por simulación y verificación de los finalistas.

## Qué hay aquí
```
CLAUDE.md                ← ORQUESTADOR (Claude Code lo carga solo)
.claude/agents/          ← 8 subagentes especializados
.claude/commands/        ← /construir-equipo: lanza el pipeline completo
knowledge/               ← 15 documentos: reglas, fórmulas, tipos, movimientos, habilidades, objetos,
                           estados/clima/hazards, roles, metodología, nivel 49 y mentas, glosario ES↔EN,
                           vocabulario de efectos, filosofía "no hay equipo perfecto", simulación
config/                  ← reglas de la partida, pesos del motor, efectos estándar, override de tipos
schemas/                 ← formato JSON de los datos normalizados
tools/pkmn/              ← motor rápido en Python (sin dependencias)
sim/                     ← simulador (Node + pokemon-showdown + @smogon/calc)
tests/                   ← tests (daño validado con Bulbapedia; simulador reproducible)
data/ejemplo/            ← mini dataset de 10 Pokémon para probar
data/entrada/            ← AQUÍ va tu fichero
workspace/               ← salidas de cada fase
```

## Los agentes
| # | Agente | Hace |
|---|---|---|
| 1 | `ingestor-datos` | Fichero bruto → JSON normalizado y validado (stats de Añil, nombres ES/EN/Showdown) |
| 2 | `oraculo-mecanicas` | Codifica habilidades y objetos (incluidos los de Añil) y sus equivalentes para Showdown; ranking de habilidades |
| 3 | `evaluador-individual` | 2–4 mejores sets por Pokémon, ranking, joyas y trampas. Se paraleliza por lotes |
| 4 | `analista-amenazas` | Meta sintético: lo mejor del pool + arquetipos por tipo + amenazas conceptuales; matriz de enfrentamientos |
| 5 | `arquitecto-equipo` | GA con varias semillas → finalistas diversos → simulación → refinado → calibración |
| 6 | `asesor-naturalezas` | Reparte las mentas por ganancia marginal (confirmada por simulación) |
| 7 | `critico-red-team` | Lee las partidas perdidas, clasifica problemas por gravedad y propone cambios verificados. No exige perfección |
| 8 | `estratega-informe` | Informe final: equipo en formato Showdown, preparación en el juego, plan de juego, velocidades, riesgos aceptados |

## Cómo usarlo
1. Requisitos: **Claude Code**, **Python 3.10+** y **Node 18+**.
2. `cd pokemon-team-agents/sim && npm install && cd ..`
3. Comprueba: `python -m unittest discover -s tests -v`
4. Rellena `config/reglas.json`: **mentas disponibles**, MTs que tienes, ¿Modo Inverso?, ¿se puede cambiar la habilidad?
5. Copia tu fichero en `data/entrada/`.
6. Abre Claude Code en la carpeta (`claude`) y escribe `/construir-equipo`. Opcional: `/construir-equipo quiero a Gyarados sí o sí`.

### Probar sin tu fichero
```bash
D="--datos data/ejemplo"
python -m tools.pkmn.cli $D validar
python -m tools.pkmn.cli $D sets
python -m tools.pkmn.cli $D amenazas
python -m tools.pkmn.cli $D equipo --generaciones 80
python -m tools.pkmn.cli $D simular --top 5 --n 4 --random-rivales 20
python -m tools.pkmn.cli $D refinar --rondas 2 --n 4 --random-rivales 20
python -m tools.pkmn.cli $D calibrar --top 8 --aleatorios 12 --n 2 --random-rivales 10
python -m tools.pkmn.cli $D exportar workspace/05_equipos/top_equipos.json 0
```

## Limitaciones conocidas (los agentes las compensan con juicio)
- El bot del simulador es heurístico y omnisciente: **ordena** bien los equipos, pero su winrate no es el winrate real contra humanos. Infrautiliza Relevo, Espacio Raro, Truco y clima manual.
- Lo exclusivo de Añil que no existe en Showdown necesita un equivalente (lo asigna el oráculo; el simulador avisa).
- Los equipos "random de otro jugador" salen del generador de Random Battle de Showdown: un rival exigente, no idéntico a lo que tendrán tus amigos antes del 5.º gimnasio.
