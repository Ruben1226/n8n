---
description: Ejecuta el pipeline completo de agentes para diseñar el mejor equipo con el fichero de data/entrada/
---

Actúa como ORQUESTADOR siguiendo `CLAUDE.md` al pie de la letra.

1. Lee `knowledge/00-reglas-de-la-partida.md` y `config/reglas.json`. Si falta información que solo sabe el jugador (mentas, MTs, objetos, IVs), pregúntala ahora en una sola tanda.
2. Ejecuta los tests del motor.
3. Lanza las fases 1 → 8 con sus subagentes, respetando los puntos de control con el jugador.
4. Termina con un resumen del equipo y la ruta a `workspace/final/informe_equipo.md`.

Argumentos opcionales del usuario: $ARGUMENTS. Por ejemplo, Pokémon que deben ir sí o sí en el equipo (pásalos como `--fijar` al arquitecto) o un arquetipo preferido.
