# 00 · Reglas de la partida (FUENTE DE VERDAD)

> Todos los agentes leen este fichero primero. Si algo de aquí contradice al competitivo estándar, **manda esto**.
> La versión ejecutable está en `config/reglas.json`. Si cambias una regla, cámbiala en los dos sitios.

## Contexto
- **Juego:** Pokémon Añil, un fangame en RPG Maker XP / Essentials que reimagina Rojo/Azul con mecánicas modernas e incluye Pokémon de las 9 generaciones.
- **Añil modifica stats base** de muchos Pokémon respecto a los oficiales (la Pokédex del juego lo muestra). **Usa siempre los del fichero.**
- Añil Definitive Edition tiene **Megaevoluciones** (incluidas las de Leyendas Z-A) y modos especiales: Randomlocke personalizable, **Modo Inverso** (tabla de tipos invertida) y Modo VGC (dobles). Esta partida es singles; si es inversa, `modo_inverso: true`.
- **Partida randomizada:**
  - Las habilidades, los movimientos y los learnsets **no tienen por qué coincidir** con los oficiales.
  - Puede haber movimientos y habilidades exclusivos de Añil.
  - **Los datos del fichero del jugador son la única verdad.** Nunca asumas el learnset ni la habilidad oficial de un Pokémon.
- **Rival:** colegas humanos, cada uno con su propia partida random.
  - **No hay meta.** No optimices contra el meta de Smogon.
  - Optimiza contra principios generales, contra arquetipos genéricos y contra lo mejor del propio pool, que sale del mismo randomizer y por eso es representativo.

## Formato
| Regla | Valor |
|---|---|
| Formato | Singles 6 vs 6 |
| Nivel | **49** (todos) |
| EVs | **0 en todos los stats** |
| IVs | Los reales de cada Pokémon. Si no se conocen, se asume 31 y se marca como SUPUESTO en el informe |
| Naturalezas | Las actuales. Se pueden cambiar con **mentas** (cantidad limitada, ver `reglas.json → mentas_disponibles`) |
| Movimientos prohibidos | **Homenaje Póstumo** (Last Respects) |
| Cláusula de sueño | No se puede dormir a un Pokémon rival si ya hay otro rival dormido por ti |
| Boosts / setup | **Sin límite** (no hay cláusula de Relevo ni de boosts) |
| Cláusula de especie | Asumida (no repetir Pokémon) |
| Cláusula de objeto | No asumida. Se permiten repeticiones si tienes varias unidades del objeto |
| MTs | Solo las que el jugador posee (`mts_disponibles`) |

## Consecuencias estratégicas de estas reglas
1. **Nivel 49 y 0 EVs comprimen los stats.**
   - Las diferencias de stats base pesan menos en valor absoluto que a nivel 100 con EVs.
   - La **naturaleza (±10 %)** y los **IVs** se notan mucho, sobre todo en los empates de velocidad.
   - A nivel 49: `stat = floor((floor((2·Base + IV)·49/100) + 5) · naturaleza)` y `PS = floor((2·Base + IV)·49/100) + 59`.
   - Cada punto de stat base ≈ 0,98 puntos de stat final. Con IV 31, la naturaleza da ±10 % sobre unos 100–160 puntos, es decir, **±10–16 puntos**.
2. **Los daños fijos** (Movimiento Sísmico, Tinieblas) hacen **49 PS exactos**. A este nivel los PS rondan 120–200, así que son el 25–40 % de la vida. Son muy útiles en muros con poco ataque.
3. **Setup sin límite:** Danza Dragón, Danza Espada, Paz Mental, Maquinación, Relevo y Rizo Defensa son legales. Los **Pokémon con Ignorante**, la **fase** (Remolino, Rugido, Niebla Clara) y **Mofa** ganan valor como contra.
4. **Cláusula de sueño:**
   - El sueño sigue siendo fortísimo (dormir a uno = 6 contra 5 durante varios turnos), pero solo puedes tener un rival dormido a la vez.
   - Basta **un** usuario de sueño fiable; dos aportan poco.
   - Spore, Somnífero e Hipnosis (60 %) no valen lo mismo: pondera la precisión.
5. **Sin Homenaje Póstumo:** se elimina de los learnsets antes de cualquier cálculo; el motor ya lo hace.
6. **Mentas limitadas:** son un recurso escaso. Las asigna el agente `asesor-naturalezas` donde más ganancia marginal den (ver `knowledge/10`).
7. **Rival humano sin meta:** habrá variedad extrema por el random. El equipo debe ser **robusto**:
   - Pocas debilidades compartidas.
   - Respuestas a cada arquetipo (sweeper físico, sweeper especial, setup, muro, stall, clima).
   - Velocidad suficiente o prioridad.
   - Un plan de victoria claro.

## Filosofía
**No existe el equipo perfecto** (ver `knowledge/13`). Se busca el mayor winrate, aceptando huecos razonables.

## Pendiente de confirmar con el jugador (el orquestador debe preguntar si no está en los datos)
- Número de mentas disponibles.
- Si Añil usa la división físico/especial por movimiento (casi seguro que sí, por ser Essentials moderno) y si existe el tipo Hada.
- Si hay movimientos o habilidades con efectos distintos a los oficiales.
- Lista de MTs y objetos en propiedad, con cantidades.
- IVs de cada Pokémon (¿el juego tiene juez de IVs?).
- Mecánica de clima en Añil: ¿granizo o nieve?
- ¿Partida en Modo Inverso? ¿Megaevolución disponible antes del 5.º gimnasio?
