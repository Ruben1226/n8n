# 08 · Roles de Pokémon y arquetipos de equipo

## Roles individuales (etiquetas en `role_tags` de cada set)
| Rol | Definición | Señales en los datos |
|---|---|---|
| **Lead / colocador de hazards** (`hazard_set`) | Abre la partida y pone Trampa Rocas o Púas | Movimiento de hazard, idealmente con Banda Focus o aguante |
| **Sweeper con setup** (`setup_wincon`) | Se potencia y barre al final de la partida | Setup + STAB fuerte + cobertura + velocidad (o prioridad) |
| **Wallbreaker** | Rompe muros con potencia bruta | Ataque o At. Esp. altos + objeto Elegido o Vidasfera + cobertura |
| **Revenge killer** (`speed_control`) | Entra tras una baja aliada y remata al sweeper rival | Pañuelo Elegido, prioridad o velocidad muy alta |
| **Muro físico / especial** | Aguanta un lado del espectro | Defensa o Def. Esp. y PS altos, recuperación, estado |
| **Pivote** (`pivot`) | Mantiene el momentum cambiando con ventaja | Ida y Vuelta, Voltiocambio o Teletransporte, Regeneración, aguante |
| **Control de hazards** (`hazard_remove`) | Mantiene tu lado limpio | Giro Rápido o Despejar |
| **Spreader de estados** (`status_spreader`) | Neutraliza amenazas | Fuego Fatuo, Onda Trueno, Tóxico, sueño |
| **Anti-setup** | Para a los sweepers rivales | Ignorante, Remolino, Rugido, Niebla Clara, Mofa, Otra Vez, Juego Sucio |
| **Cleric** (`cleric`) | Cura estados del equipo | Campana Cura, Aromaterapia, Deseo |

## Check vs counter
- **Check:** gana el 1 contra 1 si entra gratis (tras una baja o un pivote), normalmente por velocidad y daño.
- **Counter:** puede entrar recibiendo un ataque del rival y aun así ganar.
- Objetivo: cada amenaza relevante tiene **≥ 1 counter o ≥ 2 checks** en el equipo. El motor calcula `check` y `counter` en `matriz.json`.

## Arquetipos de equipo (elige uno como plan principal)
| Arquetipo | Idea | Encaja si el pool tiene… |
|---|---|---|
| **Hyper Offense** | Lead con hazards + 4–5 atacantes y sweepers. Presión desde el turno 1 | Varios sweepers rápidos con setup o habilidades top (Potencia, Adaptable, Impulso) |
| **Bulky Offense / Balance** | 2–3 atacantes robustos + 2 pivotes o muros + hazards. **El más robusto contra rivales impredecibles** | Mezcla de atacantes y Pokémon con aguante y recuperación |
| **Stall** | Muros + hazards + estados; gana por desgaste | Muchos muros con recuperación fiable y Tóxico. Es frágil al setup si no hay Ignorante o fase |
| **Clima** | Setter + abusadores (Nado Rápido, Clorofila…) | Setter por habilidad + ≥ 2 abusadores |
| **Espacio Raro** | Setter + atacantes lentos y fuertes | Varios Pokémon muy lentos y potentes |
| **Volt-turn** | Pivotes rápidos que crean ventaja con cada cambio | Varios usuarios de Ida y Vuelta o Voltiocambio + wallbreakers |

**Recomendación por defecto** para una partida random contra amigos: **Bulky Offense / Balance**, con:
- 1 colocador de hazards.
- 1 control de velocidad (Pañuelo Elegido o prioridad).
- 1–2 condiciones de victoria (sweepers con setup).
- 1 anti-setup.
- 1–2 pivotes o muros con recuperación.

Cambia de arquetipo solo si el pool lo pide claramente (por ejemplo, 3 Pokémon con Nado Rápido y un setter de lluvia).
