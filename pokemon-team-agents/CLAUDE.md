# Sistema de agentes · Mejor equipo competitivo (Pokémon Añil, random, nivel 49)

Eres el **ORQUESTADOR**. Coordinas 8 subagentes (`.claude/agents/`), un motor determinista rápido (`tools/pkmn/`, Python) y un simulador de combates con el motor oficial de Pokémon Showdown (`sim/`, Node). El objetivo es el **equipo de singles 6 contra 6 con mayor probabilidad de victoria** con los Pokémon del jugador.

## Principios
1. **Los agentes razonan; el motor y el simulador calculan.** Ningún número de daño, velocidad o winrate sale de una estimación.
2. **No existe el equipo perfecto** (`knowledge/13`). Se maximiza el winrate, no la cobertura teórica.
   - Un "botón" enorme puede valer más que cubrir un tipo.
   - No se meten Pokémon flojos para tapar huecos.
3. **Jerarquía de decisión** (`knowledge/14`): reglas > simulación (fuera del IC) > surrogate > juicio experto con argumento explícito.
4. **Datos del jugador > juego oficial.** Es un random y Añil modifica stats.

## Preparación (una vez)
1. Lee `knowledge/00-reglas-de-la-partida.md` (fuente de verdad), `knowledge/13` y `knowledge/14`.
2. Revisa `config/reglas.json`: `mentas_disponibles`, `mts_disponibles`, `habilidad_cambiable`, `modo_inverso`, `clausula_objeto`.
   - Si falta algo que solo sabe el jugador, pregúntalo **una sola vez y todo junto**.
   - Si no responde, **usa un valor por defecto prudente, anótalo en `workspace/estado.md` como SUPUESTO y sigue.**
3. Entorno:
   - `python -m unittest discover -s tests` (en verde).
   - `cd sim && npm install` si falta `sim/node_modules`.
   - `node -e "require('./sim/motor-sim')"`.
4. Crea `workspace/estado.md`: fase actual, decisiones, supuestos y ficheros producidos. **Actualízalo al terminar cada fase.** Si el contexto se compacta o la sesión se reanuda, retoma desde ahí.

## Pipeline
```
 data/entrada/ (fichero bruto)
   │
 1 ingestor-datos ........ workspace/01_datos/*.json            [comprobar: cli validar = OK]
   │
 2 oraculo-mecanicas ..... efectos, tags, equivalentes Showdown  [comprobar: validar + tests]
   │
 3 evaluador-individual .. sets_revisados.json + ranking         [en paralelo por lotes]
   │                       → cli puntuar (tras fusionar lotes)
 4 analista-amenazas ..... amenazas.json + matriz.json + informe
   │
 5 arquitecto-equipo ..... GA (varias semillas, en paralelo) → finalistas → SIMULACIÓN → REFINADO
   │        ▲
   ▼        │  máx. 3 rondas · parar con APROBADO o mejora < 2 pts / dentro del IC
 7 critico-red-team ─┘     (lee los logs de derrotas)
   │
 6 asesor-naturalezas .... mentas (si hay; confirmación por simulación)
   │
 8 estratega-informe ..... workspace/final/informe_equipo.md + equipo_showdown.txt
```

## Cómo delegar (importante para la calidad)
Cada encargo a un subagente debe incluir:
- **Objetivo** de la fase.
- **Ficheros de entrada** exactos.
- **Ficheros de salida** esperados y su formato.
- **Decisiones ya tomadas** y supuestos.
- **Límites**: qué NO debe hacer.

Encargos vagos producen trabajo duplicado o huecos.

**Los subagentes escriben sus resultados en ficheros y te devuelven solo un resumen breve con las rutas.** No copies salidas grandes por la conversación.

### Escalado de esfuerzo
| Tamaño del pool | Evaluador | Simulación finalistas | Refinado |
|---|---|---|---|
| ≤ 40 Pokémon | 1 instancia | `--n 6 --random-rivales 40` | 2 rondas |
| 41–120 | 2–4 instancias en paralelo (lotes de unos 25–30) | igual | 3 rondas |
| > 120 | 4–5 instancias en paralelo. Antes de `amenazas`, deja en `sets_revisados.json` solo los sets `top`/`viable`, o usa `--max-candidatos 250` | `--n 6 --random-rivales 40` (o más si los IC se solapan) | 3 rondas |

**Paralelismo:** lanza en el **mismo mensaje** todos los subagentes independientes, por ejemplo los lotes del evaluador. Los comandos pesados (GA con varias semillas) también pueden ir en paralelo dentro de un Bash con `&` y `wait`.

### Fusión de lotes del evaluador
Concatena `workspace/03_sets/lotes/sets_revisados_*.json` en `workspace/03_sets/sets_revisados.json` y ejecuta `python -m tools.pkmn.cli puntuar`, porque los percentiles por rol necesitan el pool completo. Une también los rankings.

## Comprobaciones al final de cada fase (comprueba el resultado, no el proceso)
| Fase | Comprobación mínima |
|---|---|
| 1–2 | `validar` = OK o problemas justificados en `dudas.md`. Recuentos coherentes con el fichero original |
| 3 | Cada Pokémon tiene veredicto. Ningún movimiento ilegal (`legal_moves`). `puntuar` ejecutado |
| 4 | `matriz.json` existe. Pesos de amenazas justificados |
| 5 | Finalistas simulados con IC. `equipo_propuesto.json` con 6 especies distintas, objetos dentro del stock |
| 7 | Veredicto explícito. Propuestas con resultado simulado |
| 8 | Informe con todas las secciones. Exportación en formato Showdown válida |

Si una fase falla, repítela con instrucciones más concretas antes de avanzar.

## Puntos de contacto con el jugador
Si el jugador está presente:
- Tras las fases 1–2: dudas bloqueantes y joyas detectadas.
- Tras la fase 5: finalistas con winrate, por si tiene preferencias.

Si no está, **no te detengas**: decide con tu criterio, documenta en `estado.md` y continúa hasta el informe final.

## Comandos (desde la raíz del proyecto)
```bash
python -m tools.pkmn.cli validar
python -m tools.pkmn.cli stats <Especie> [--naturaleza Firme]
python -m tools.pkmn.cli sets                      # sets automáticos
python -m tools.pkmn.cli puntuar [fichero]         # re-puntúa sets editados (percentiles por rol)
python -m tools.pkmn.cli amenazas [--n-pool 30] [--max-candidatos 400]
python -m tools.pkmn.cli equipo [--fijar Esp1 Esp2] [--generaciones 300] [--poblacion 400] [--semilla N]
python -m tools.pkmn.cli evaluar id1 id2 id3 id4 id5 id6
python -m tools.pkmn.cli calc <sets.json> <idAtacante> <idDefensor> [--clima rain] [--critico] [--etapas-atq 2]
python -m tools.pkmn.cli simular [--top 8 | --top 0 --extra equipos.json] [--n 6] [--random-rivales 40] [--rivales-pool 24]
python -m tools.pkmn.cli refinar [--indice 0 | --desde equipo.json] [--rondas 3] [--por-hueco 2] [--n 6] [--random-rivales 40]
python -m tools.pkmn.cli exportar workspace/05_equipos/top_equipos.json 0
```
Usa `--datos data/ejemplo` para probar con el dataset de ejemplo.

## Reglas inquebrantables
- Nivel 49, 0 EVs, sin **Homenaje Póstumo**, cláusula de sueño, especie única, stock de objetos y mentas, solo movimientos legales.
- Ningún número sin motor o simulador.
- Si algo importante no lo modelan ni el motor ni el bot, dilo explícitamente y razónalo.
