# 09 · Metodología de construcción de equipos

> Lee antes `knowledge/13`: **no existe el equipo perfecto**. Estos principios son guías para ganar más partidas, no casillas obligatorias.

## Principios (en orden de importancia)
1. **Condición de victoria clara.** ¿Cómo gana este equipo? Ejemplos: "Gyarados +1 barre tras quitar al muro físico" o "desgaste con hazards y Tóxico".
2. **Robustez defensiva:**
   - Ninguna debilidad compartida por 3 o más miembros.
   - Para cada tipo de ataque, al menos un miembro que lo resista o sea inmune y pueda entrar.
3. **Respuestas a arquetipos:** sweeper físico rápido, sweeper especial rápido, setup bulky, muro físico, muro especial, Espacio Raro, clima. Cada uno con ≥ 1 counter o ≥ 2 checks.
4. **Control de velocidad:** al menos 2 miembros rápidos, o 1 rápido + prioridad o Pañuelo Elegido.
5. **Roles cubiertos:** hazards, control de hazards (si hay débiles a Roca), pivote, anti-setup, spreader de estados.
6. **Calidad individual:** a igualdad de encaje, gana el Pokémon más fuerte.
7. **Restricciones duras:** especie única, objetos disponibles, mentas disponibles, movimientos prohibidos.

## Proceso iterativo
```
1. Núcleo: elige 1-2 Pokémon top (wincon) del ranking del evaluador.
2. Tapa debilidades del núcleo: ¿qué tipos lo amenazan? Añade quien resista/inmune y amenace a esos tipos.
3. Roles: añade hazards / speed control / anti-setup que falten.
4. Revisa la matriz de amenazas: cada amenaza sin respuesta → busca un sustituto que la responda sin romper lo anterior.
5. Ajusta sets: objetos (únicos), naturalezas (mentas), habilidad, 4.º movimiento.
6. Crítico: busca el peor matchup posible; si es inaceptable, vuelve al 4.
```
`teamsearch.py` automatiza los pasos 1–5 con un algoritmo genético. **Los agentes deben:**
- Revisar los top 10 del motor (no solo el #1): diversidad de arquetipos.
- Corregir lo que el motor no ve:
  - Habilidades `note`.
  - Combos: Tóxico + Protección + Restos, Trampa Rocas + presión de Pañuelo, Bostezo + fase.
  - Sinergia de clima.
  - Pivotes que llevan a los wallbreakers.
- Proponer variaciones con `--fijar` y reevaluarlas con `evaluar`.

## Función objetivo del motor (surrogate rápido; pesos en `config/pesos_equipo.json`)
| Componente | Cómo se calcula |
|---|---|
| `amenazas` | Por amenaza: 0,5 por check (máx. 2) + 0,5 si hay counter, ponderado por peso |
| `presion_ofensiva` | Por amenaza: mayor daño mínimo que le hace algún miembro (tope 100 %) + bonus si alguien la deja KO de un golpe. **Premia los "botones"** |
| `defensa_tipos` | Rendimiento decreciente: 2.ª resistencia vale menos; solo penaliza a partir del 2.º débil |
| `roles` | Suma de pesos de los roles deseados presentes |
| `velocidad` | Miembros rápidos o con control de velocidad (máx. 3) |
| `calidad_individual` | Media del **percentil dentro del rol** de cada set |
| Penalizaciones | **Eslabón débil** (miembro < percentil 40 de su rol); debilidad compartida (blanda, ×0,25 si está compensada ofensivamente); especie repetida; objetos o mentas por encima del stock |

- **El surrogate no es la verdad:** sirve para explorar miles de equipos.
- **La verdad operativa es la simulación** (`knowledge/14`).
- Los pesos se pueden **calibrar con la simulación** (`cli calibrar`): una regresión dice qué componentes predicen de verdad el winrate. Así el equilibrio cobertura/potencia lo deciden los datos (`knowledge/13`).

**El desglose de cada equipo se guarda en `top_equipos.json`.** Úsalo para explicar decisiones.

## Errores típicos a evitar
- 6 atacantes sin ningún plan contra un muro con recuperación.
- Ninguna respuesta a un sweeper con setup (los boosts son ilimitados). **Error grave en esta partida.**
- 3 o más Pokémon lentos sin Espacio Raro.
- Depender de movimientos de menos del 80 % de precisión para ganar enfrentamientos clave.
- Usar Elegidos en Pokémon con 2 ataques útiles.
- Dos usuarios de sueño (cláusula).
- Gastar mentas en Pokémon que no entran en el equipo final.
