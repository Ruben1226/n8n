# 14 · Validación por simulación (motor oficial de Pokémon Showdown)

## Por qué
- El motor Python es un **surrogate** rápido: evalúa enfrentamientos 1 contra 1, cobertura y roles en milisegundos, y permite explorar miles de equipos.
- Pero no ve la partida entera: hazards acumulados, desgaste, cambios, momentum, setup a mitad de partida.
- La investigación sobre construcción automática de equipos (un sistema que llegó al top 33 mundial en Showdown) usa justo esto:
  - Un **algoritmo genético** cuya función de fitness es **simular el equipo contra muchos rivales**.
  - Comprobación final de los mejores, porque la estimación tiene margen de error.
- Este sistema replica ese esquema: **búsqueda barata → simulación de los finalistas → refinado local guiado por simulación**.

## Cómo funciona (`sim/`)
- **Motor de combate:** `pokemon-showdown` (el simulador oficial, todas las mecánicas Gen 9). Formato `gen9customgame`, con:
  - Sleep Clause Mod, Species Clause, OHKO Clause, Evasion Moves Clause.
  - Inverse Mod si `modo_inverso`.
  - Nivel 49 y 0 EVs.
- **Datos de Añil:** los tipos y stats base de `pokemon.json` se inyectan en las especies de Showdown, porque Añil modifica stats respecto a los oficiales.
- **Bot (gana ~85 % a un bot aleatorio con el mismo equipo; parámetros ajustados por barrido, ver `sim/motor-sim.js → P`):** heurístico y **omnisciente** (ve el equipo rival). Usa `@smogon/calc` para estimar daños y sigue estas prioridades:
  1. Rematar si puede.
  2. Prioridad que remata.
  3. Cambiar si le van a debilitar antes y hay un relevo que aguanta.
  4. Hazards.
  5. Setup seguro.
  6. Recuperación.
  7. Estados útiles, respetando la cláusula de sueño.
  8. Quitar hazards.
  9. Mayor daño, prefiriendo pivotes.

  Ambos bandos usan el mismo bot: es un **instrumento de medida**, no un rival humano.
- **Rivales:**
  - **Candidatos entre sí** (round-robin).
  - **Equipos del propio pool** muestreados entre los sets buenos. Tus colegas juegan el mismo randomizer, así que son representativos.
  - **Equipos "random de otro jugador"**: generador oficial de Random Battle de Showdown, normalizado a nivel 49 y 0 EVs. Simulan Pokémon que tú no tienes pero tus colegas sí podrían tener.
- **Números aleatorios comunes:** todos los equipos juegan con las **mismas semillas** contra los mismos rivales. Así las diferencias entre equipos son reales y no ruido.
- **Velocidad:** unos 90 ms por partida y núcleo; se usan todos los núcleos.

## Comandos
```bash
python -m tools.pkmn.cli simular --top 8 --n 6 --random-rivales 40 --rivales-pool 24   # finalistas del GA
python -m tools.pkmn.cli simular --top 0 --extra workspace/07_sim/mis_equipos.json     # equipos propios
python -m tools.pkmn.cli refinar --indice 0 --rondas 3 --por-hueco 2 --n 6 --random-rivales 40
```
**Salidas en `workspace/07_sim/`:**
- `*_resultados.json`, que incluye para cada equipo:
  - winrate, IC 95 %, winrate contra random y contra el pool, peores rivales, turnos medios.
  - Por miembro: veces debilitado y KOs.
- `logs/`: registros de partidas perdidas, para que el crítico los lea.

## Refinado y sobreajuste
`refinar` elige variantes midiendo contra un conjunto fijo de rivales, así que puede **sobreajustarse** a esos rivales. Por eso, al terminar, vuelve a enfrentar el original con el refinado contra **rivales nuevos** (otra semilla, otros equipos del pool y otros equipos random). Solo cuenta la mejora que se mantiene ahí.

## Calibrar el surrogate con la simulación
`python -m tools.pkmn.cli calibrar --top 15 --aleatorios 15 --n 4 --random-rivales 30`
1. Simula unos 30 equipos: los mejores del GA más equipos aleatorios, para tener variedad.
2. Ajusta una regresión del winrate sobre los componentes del desglose.
3. Escribe `config/pesos_equipo_calibrados.json` con:
   - La correlación de Spearman entre surrogate y simulación, antes y después.
   - Los pesos sugeridos.

**Si la correlación mejora claramente (> +0,1 con ≥ 25 equipos)**, adopta los pesos sugeridos y repite la búsqueda GA. Es la forma de que el equilibrio entre cobertura y potencia lo decidan las partidas y no una opinión.

## Cómo interpretar
- **IC 95 % (Wilson):** si los intervalos de dos equipos se solapan mucho, la diferencia puede ser ruido.
  - Con unas 400 partidas por equipo, el IC es de ±5 puntos.
  - Para decidir entre finalistas parecidos, sube `--n` o `--random-rivales`.
- **winrate_vs_random vs winrate_vs_pool:**
  - Alto contra el pool y bajo contra random: el equipo explota debilidades de tu propio pool, pero puede sufrir contra Pokémon que no tienes.
  - Lo ideal es que ambos sean altos.
- **Miembros:** uno que muere primero en la mayoría de derrotas y hace pocos KOs es candidato a cambio. **Pero mira los logs**: quizá se sacrifica bien.
- **Peores rivales:** el crítico debe abrir sus logs y explicar *por qué* se pierde.

## Decisiones de diseño del bot (probadas, no supuestas)
- Un bot con **previsión de 1 turno** (lookahead) se probó y perdió el 71 % de las partidas contra el heurístico: cambiaba demasiado. **Descartado.**
- Barrido de parámetros contra la versión base, validado con semillas nuevas (400 partidas por variante):
  - Cambiar solo ante una amenaza de KO **si el relevo es claramente bueno** (`switchKO 0.65`).
  - Hacer setup con algo más de valentía (`setupSafety 1.5`).
  - Resultado: **~60–64 % contra la versión anterior** y 85 % contra un bot aleatorio.
- **Comprobado: no hay sesgo de lado** (p1 gana el 51,7 % de 300 espejos).

## Limitaciones (decláralas en el informe)
- El bot no predice, no hace "mind games" y juega con información completa. Un humano jugará distinto.
  - Por eso la simulación **ordena** equipos de forma fiable, pero **el winrate absoluto no es el winrate real**.
- El bot infrautiliza estrategias complejas: Relevo, Espacio Raro, clima manual, Truco, Otra Vez. Si el equipo depende de ellas, la simulación lo subestima. Razónalo aparte.
- **Movimientos, habilidades u objetos exclusivos de Añil** que no existen en Showdown: el oráculo debe asignarles un equivalente (`showdown_moves`, `showdown_ability`, `showdown_item`) o se ignoran. El simulador avisa de cada caso.
- Los equipos "random" de Showdown incluyen Pokémon de todas las generaciones con sets competitivos. Es un rival exigente, no necesariamente igual a lo que tendrán tus colegas antes del 5.º gimnasio.

## Jerarquía de decisión
1. **Reglas de la partida** (inviolables).
2. **Simulación** con diferencia fuera del IC.
3. **Motor surrogate** (desglose: amenazas, presión ofensiva…).
4. **Juicio experto**. Solo puede contradecir a 2 y 3 con un argumento explícito sobre algo que ni el motor ni el bot modelan: "el bot no sabe usar Relevo, pero un humano sí".
