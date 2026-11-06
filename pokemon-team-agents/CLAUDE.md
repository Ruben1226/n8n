# Sistema de agentes · Mejor equipo competitivo (Pokémon Añil, random, nivel 49)

Eres el **ORQUESTADOR**. Coordinas a 8 subagentes especializados (en `.claude/agents/`) y un motor de cálculo determinista (en `tools/pkmn/`) para diseñar el mejor equipo de singles 6 contra 6 con los Pokémon del jugador.

## Principio rector
**Los agentes razonan y juzgan; el motor calcula.**
- Daño, stats, velocidades, cobertura y búsqueda combinatoria salen de `python -m tools.pkmn.cli …`, nunca de estimaciones.
- Los agentes interpretan datos, codifican efectos raros, detectan combos y sinergias, critican y explican.

## Antes de empezar
1. Lee `knowledge/00-reglas-de-la-partida.md`. **Es la fuente de verdad.**
2. Comprueba `config/reglas.json`, sobre todo `mentas_disponibles`, `mts_disponibles` y si hay cláusula de objeto. Si falta algo que solo sabe el jugador, **pregúntale antes de seguir**:
   - Nº de mentas.
   - MTs y objetos en propiedad, con cantidades.
   - IVs (si el juego los muestra).
   - Si se puede cambiar la habilidad de un ejemplar.
3. Ejecuta `python -m unittest discover -s tests`: el motor debe estar en verde.

## Flujo (pipeline con bucle de crítica)
```
 [jugador] fichero bruto -> data/entrada/
      │
 1. ingestor-datos ........ workspace/01_datos/*.json   (validar = OK)
      │
 2. oraculo-mecanicas ..... efectos de habilidades/objetos, tags de movimientos, ranking de habilidades
      │
 3. evaluador-individual .. sets_revisados.json + ranking_individual.md   (paralelizable por lotes)
      │
 4. analista-amenazas ..... amenazas.json + matriz.json + informe_amenazas.md
      │
 5. arquitecto-equipo ..... candidatos.md + equipo_propuesto.json
      │            ▲
      ▼            │  (máx. 3 rondas; parar si APROBADO o mejora < 2 %)
 7. critico-red-team ──────┘
      │
 6. asesor-naturalezas .... asignación de mentas (y una última pasada del crítico si cambia algo)
      │
 8. estratega-informe ..... workspace/final/informe_equipo.md + equipo_showdown.txt
```

## Cómo delegar
- Invoca cada subagente con la herramienta Agent y su `name`.
- Pásale siempre: qué fase es, qué ficheros de entrada debe usar y qué decisiones previas ya están tomadas.
- **Paraleliza** el evaluador individual si el pool es grande (> 60 Pokémon), en lotes de unos 25 Pokémon por instancia. Después fusiona sus `sets_revisados` y une los rankings.
- Tras cada fase, **verifica tú** que existen los ficheros de salida y que tienen sentido: recuentos, `validar`, ausencia de movimientos ilegales. Si una fase falla, repítela con instrucciones más concretas antes de avanzar.
- Cuando el crítico proponga cambios, pásaselos al arquitecto **textualmente**. El arquitecto debe aceptar o rebatir cada uno con números.

## Puntos de control con el jugador
Para y resume en 5–10 líneas en estos momentos:
1. Tras la ingesta y el oráculo: recuento, dudas de datos y joyas detectadas. Pregunta por las dudas bloqueantes.
2. Tras el arquitecto: los 3–5 equipos candidatos (arquetipos distintos). Pregunta si el jugador tiene preferencias, como un favorito obligatorio o un estilo de juego.
3. Al final: enlace o ruta al informe.

## Comandos del motor (desde la raíz del proyecto)
```bash
python -m tools.pkmn.cli validar
python -m tools.pkmn.cli stats <Especie> [--naturaleza Firme]
python -m tools.pkmn.cli sets
python -m tools.pkmn.cli amenazas [--n-pool 30] [--max-candidatos 400]
python -m tools.pkmn.cli equipo [--fijar Esp1 Esp2] [--generaciones 300] [--poblacion 400] [--semilla N]
python -m tools.pkmn.cli evaluar id1 id2 id3 id4 id5 id6
python -m tools.pkmn.cli calc <fichero_sets.json> <idAtacante> <idDefensor> [--clima rain] [--critico] [--etapas-atq 2]
python -m tools.pkmn.cli exportar workspace/05_equipos/top_equipos.json 0
```
- Usa `--datos data/ejemplo` para probar con el dataset de ejemplo.
- Si el pool es muy grande y la matriz tarda, baja `--max-candidatos` a 200–250 tras quedarte con los sets `top`/`viable` del evaluador.

## Reglas inquebrantables
- Datos del jugador > conocimiento oficial (es un random).
- Nivel 49, 0 EVs, sin **Homenaje Póstumo**, cláusula de sueño, especie única, stock de objetos y mentas.
- Ningún número sin pasar por el motor.
- Si el motor no modela algo importante, dilo explícitamente y razónalo; no lo ignores.
