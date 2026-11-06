# 04 · Movimientos: categorías, efectos y cómo valorarlos

## Atributos de un movimiento (esquema en `schemas/move.schema.json`)
| Atributo | Valores |
|---|---|
| Tipo | Uno de los 18 |
| Categoría | **física**, **especial** o **estado** (por movimiento, desde Gen 4) |
| Potencia | Número, o `null` si es de estado |
| Precisión | % o `null` si nunca falla |
| PP | Número |
| Prioridad | +5 … −7 (0 lo normal) |
| Contacto | Sí o no. Activa Casco Dentado, Piel Tosca, Cuerpo Llama, Garra Dura… |
| Efecto secundario | Probabilidad de quemar, paralizar, retroceder, bajar o subir stats… Se anula con Potencia Bruta, que a cambio da ×1.3 |
| Etiquetas | Ver abajo y `knowledge/12` |

## Etiquetas de movimiento que usa el sistema
**Efectos de daño y propiedades** (las usan habilidades como Puño Férreo o Mandíbula Fuerte):
- `contact`, `punch`, `bite`, `sound`, `pulse`, `slicing`, `bullet`, `recoil`, `secondary`, `drain`, `multi_hit`.

**Penalizaciones en la valoración:**
| Etiqueta | Significado | Factor |
|---|---|---|
| `recharge` | Hiperrayo | ×0.5 |
| `charge` | Rayo Solar sin sol, Vuelo | ×0.55 |
| `self_ko` | Explosión | ×0.3 |
| `self_drop` | A Bocajarro, Sofoco | ×0.88 |
| `recoil` | — | ×0.93 |
| `lock_in` | Enfado | ×0.9 |
| `unreliable` | — | ×0.7 |

**Utilidad:**
| Etiqueta | Ejemplos |
|---|---|
| `setup_atk` | Danza Espada, Corpulencia, Afilagarras |
| `setup_spa` | Maquinación, Paz Mental, Danza Aleteo |
| `setup_spe` | Agilidad, Autotomía |
| `setup_mixed` | Danza Dragón, Danza Aleteo, Rompecoraza, Cambio de Marcha |
| `recovery` | Recuperación, Respiro, Amortiguador, Síntesis, Descanso, Drenadoras, Deseo |
| `hazard_set` | Trampa Rocas, Púas, Púas Tóxicas, Red Viscosa |
| `hazard_remove` | Giro Rápido, Despejar, Tidy Up (Gen 9) |
| `pivot` | Ida y Vuelta, Voltiocambio, Viraje, Teletransporte (Gen 8+), Chuletazo, Última Palabra |
| `status_burn` | Fuego Fatuo |
| `status_para` | Onda Trueno, Deslumbrar, Látigo Glacial |
| `status_toxic` | Tóxico |
| `status_sleep` | Espora, Somnífero, Hipnosis, Canto, Bostezo |
| `phaze` | Remolino, Rugido, Cola Dragón, Llave Giro |
| `screens` | Reflejo, Pantalla de Luz, Velo Aurora |
| `taunt` | Mofa |
| `trick` | Truco, Trapicheo |
| `protect` | Protección, Detección |
| `speed_control` | Onda Trueno, Viento Afín, Espacio Raro, Red Viscosa, Viento Hielo, Electrotela… |
| `cleric` | Campana Cura, Aromaterapia |
| `fixed_level` | Movimiento Sísmico, Tinieblas |
| `target_def` | Psicocarga |
| `foul_play` | Juego Sucio |
| `body_press` | Plancha Corporal |

## Cómo valorar un ataque (lo que hace `setgen.py`)
`valor = Potencia × modificadores de habilidad × STAB × precisión × golpes × penalizaciones × (1.08 si tiene prioridad)`, ponderado por el stat atacante.

Después la **cobertura** se mide sobre las 171 combinaciones de tipos. El primer ataque es casi siempre el STAB más fuerte; los siguientes, los que más **cobertura marginal** añaden.

## Movimientos especialmente valiosos (si el random los da)
- **Prioridad:**
  - Velocidad Extrema (+2).
  - Ultrapuño, Puño Bala, Acua Jet, Sombra Vil, Fuerza Vil, Canto Helado, Golpe Bajo, Puño Drenaje (+1).
  - Son esenciales sin Pañuelo Elegido para rematar sweepers que van +1.
- **Setup que sube velocidad:** Danza Dragón, Danza Aleteo, Cambio de Marcha, Rompecoraza. Un buen usuario a nivel 49 puede barrer equipos enteros (los boosts son ilimitados).
- **Hazards:** Trampa Rocas es probablemente el mejor movimiento de soporte. Castiga los cambios, rompe Banda Focus y Robustez, y daña ×4 a los débiles a Roca (50 %).
- **Fuego Fatuo / Onda Trueno / Tóxico:** neutralizan atacantes físicos, sweepers rápidos y muros, respectivamente.
- **Espora / Somnífero** (fiables): un rival dormido es una ventaja enorme. Recuerda la cláusula de sueño.
- **Recuperación fiable** (50 %): convierte a un Pokémon con buen aguante en un muro real.
- **Pivotes:** mantienen el momentum y el control de los enfrentamientos.
- **Mofa:** contra soportes y setup.
- **Remolino / Rugido / Niebla Clara:** contra setup ilimitado. **Muy recomendable tener al menos una respuesta a setup.**

## Trampas comunes
- Rayo Solar sin sol, Hiperrayo, Vuelo, Bote: casi siempre malas opciones.
- Ataques con menos del 85 % de precisión: Hidrobomba, Llamarada, Megacuerno, Roca Afilada. Son válidos si no hay alternativa, pero se penalizan.
- Autodestrucción y Explosión: solo en casos muy concretos.
- **Homenaje Póstumo está PROHIBIDO.**
