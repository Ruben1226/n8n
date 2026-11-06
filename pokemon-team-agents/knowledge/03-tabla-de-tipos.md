# 03 · Tabla de tipos (Gen 6+, 18 tipos) — implementada en `tools/pkmn/typechart.py`

Si Añil modifica algo, va en `config/tabla_tipos_override.json`.

## Ofensiva: contra qué es súper eficaz (×2) / poco eficaz (×½) / sin efecto (×0)
| Atacante | ×2 contra | ×½ contra | ×0 contra |
|---|---|---|---|
| Normal | — | Roca, Acero | Fantasma |
| Fuego | Planta, Hielo, Bicho, Acero | Fuego, Agua, Roca, Dragón | — |
| Agua | Fuego, Tierra, Roca | Agua, Planta, Dragón | — |
| Eléctrico | Agua, Volador | Eléctrico, Planta, Dragón | Tierra |
| Planta | Agua, Tierra, Roca | Fuego, Planta, Veneno, Volador, Bicho, Dragón, Acero | — |
| Hielo | Planta, Tierra, Volador, Dragón | Fuego, Agua, Hielo, Acero | — |
| Lucha | Normal, Hielo, Roca, Siniestro, Acero | Veneno, Volador, Psíquico, Bicho, Hada | Fantasma |
| Veneno | Planta, Hada | Veneno, Tierra, Roca, Fantasma | Acero |
| Tierra | Fuego, Eléctrico, Veneno, Roca, Acero | Planta, Bicho | Volador |
| Volador | Planta, Lucha, Bicho | Eléctrico, Roca, Acero | — |
| Psíquico | Lucha, Veneno | Psíquico, Acero | Siniestro |
| Bicho | Planta, Psíquico, Siniestro | Fuego, Lucha, Veneno, Volador, Fantasma, Acero, Hada | — |
| Roca | Fuego, Hielo, Volador, Bicho | Lucha, Tierra, Acero | — |
| Fantasma | Psíquico, Fantasma | Siniestro | Normal |
| Dragón | Dragón | Acero | Hada |
| Siniestro | Psíquico, Fantasma | Lucha, Siniestro, Hada | — |
| Acero | Hielo, Roca, Hada | Fuego, Agua, Eléctrico, Acero | — |
| Hada | Lucha, Dragón, Siniestro | Fuego, Veneno, Acero | — |

## Conceptos clave para construir equipos
- **Cobertura ofensiva:** combinaciones de tipos de ataque que golpean neutro o súper eficaz a casi todo. Clásicas:
  - **"Bolt-Beam" (Eléctrico + Hielo):** muy pocas combinaciones de tipos la resisten a la vez.
  - **"EdgeQuake" (Roca + Tierra):** cubre casi todo; la paran Planta/Lucha, Planta/Bicho y los voladores que resisten Roca.
  - **Fantasma + Lucha:** solo la paran Normal/Fantasma (y habilidades como Superguarda).
  - **Hielo + Tierra:** muy amplia; la frenan sobre todo los Acero/Volador y los Agua/Planta-resistentes.
  - **Verifica siempre con el motor**, porque en random las habilidades (Levitación, Absorbe Agua…) cambian las inmunidades reales.
- **El motor mide la cobertura** sobre las **171 combinaciones de tipos** (18 monotipos + 153 dobles), con rendimiento decreciente: log(1 + daño). Un set que golpea fuerte a todo vale más que uno que hace ×4 a pocos.
- **Sinergia defensiva:** cada debilidad de un miembro debería estar cubierta por la resistencia o inmunidad de otro, que entra en ese ataque. Núcleos clásicos:
  - **Fuego / Agua / Planta.**
  - **Dragón / Acero / Hada.**
  - **Fantasma / Siniestro / Lucha** (núcleo ofensivo).
  - **Tierra / Volador / Agua.**
- **Debilidad compartida:** 3 o más miembros débiles al mismo tipo, o 2 débiles sin ningún resistente. Penaliza fuerte.
- **Tipos defensivamente buenos:**
  - Acero: 10 resistencias y 1 inmunidad.
  - Hada: inmune a Dragón.
  - Fantasma: inmune a Normal y Lucha.
  - Volador / Levitación: inmune a Tierra.
  - Agua: pocas debilidades.
- **Tipos defensivamente malos:**
  - Hielo, Roca y Planta/Bicho tienen muchas debilidades.
  - Roca, además, sufre Agua/Planta/Lucha/Tierra/Acero, todos tipos ofensivos comunes.
- **Las habilidades cambian la tabla:** en una partida random, **Levitación, Absorbe Agua, Absorbe Fuego, Pararrayos, Herbívoro, Sebo, Filtro…** pueden aparecer en cualquier Pokémon. Cuentan como inmunidades o resistencias reales del miembro, y el motor las aplica.
