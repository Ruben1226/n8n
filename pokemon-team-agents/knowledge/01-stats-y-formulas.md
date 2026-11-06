# 01 · Stats, naturalezas, IVs/EVs y fórmulas

## Los 6 stats
| Clave | Español | Uso |
|---|---|---|
| hp | PS | Vida |
| atk | Ataque | Daño de movimientos **físicos** |
| def | Defensa | Reduce el daño **físico** recibido |
| spa | Ataque Especial | Daño de movimientos **especiales** |
| spd | Defensa Especial | Reduce el daño **especial** recibido |
| spe | Velocidad | Decide quién mueve primero dentro del mismo bracket de prioridad |

## Fórmulas (nivel L, EV = 0 en esta partida)
```
PS    = floor((2·Base + IV + floor(EV/4)) · L / 100) + L + 10
Otros = floor((floor((2·Base + IV + floor(EV/4)) · L / 100) + 5) · Naturaleza)
```
- Naturaleza: 1.1 en el stat que sube, 0.9 en el que baja, 1.0 en el resto.
- Shedinja siempre tiene 1 PS.
- **A nivel 49 con 0 EVs e IV 31:**
  - Base 100 → 115 (neutra), 126 (+), 103 (−).
  - PS base 100 → 172.

## Naturalezas (ES → EN, + / −)
| ES | EN | + | − | ES | EN | + | − |
|---|---|---|---|---|---|---|---|
| Huraña | Lonely | Atq | Def | Osada | Bold | Def | Atq |
| Audaz | Brave | Atq | Vel | Plácida | Relaxed | Def | Vel |
| Firme | Adamant | Atq | AtEsp | Agitada | Impish | Def | AtEsp |
| Pícara | Naughty | Atq | DefEsp | Floja | Lax | Def | DefEsp |
| Miedosa | Timid | Vel | Atq | Modesta | Modest | AtEsp | Atq |
| Activa | Hasty | Vel | Def | Afable | Mild | AtEsp | Def |
| Alegre | Jolly | Vel | AtEsp | Mansa | Quiet | AtEsp | Vel |
| Ingenua | Naive | Vel | DefEsp | Alocada | Rash | AtEsp | DefEsp |
| Serena | Calm | DefEsp | Atq | Grosera | Sassy | DefEsp | Vel |
| Amable | Gentle | DefEsp | Def | Cauta | Careful | DefEsp | AtEsp |

Neutras: Fuerte (Hardy), Dócil (Docile), Seria (Serious), Tímida (Bashful), Rara (Quirky).

**Las mentas** cambian el efecto de la naturaleza (no la naturaleza "real") a la de la menta. Para el cálculo es igual.

## Cambios de stats en combate (etapas)
- Van de −6 a +6. Multiplicador: `(2 + n) / 2` si n ≥ 0, y `2 / (2 − n)` si n < 0.
  - +1 = ×1.5, +2 = ×2, +6 = ×4, −1 = ×0.67, −2 = ×0.5.
- Se pierden al cambiar de Pokémon (salvo con Relevo).
- **Los críticos** ignoran las bajadas de ataque del atacante y las subidas de defensa del defensor.
- **Ignorante** (Unaware) ignora las etapas del rival.

## Velocidad
- Orden de turno: primero por **prioridad** (+5 … −7) y, dentro del mismo bracket, por velocidad efectiva.
  - Con **Espacio Raro**, dentro de cada bracket se invierte.
- Velocidad efectiva = stat × etapa × objeto (Pañuelo Elegido ×1.5) × habilidad (Nado Rápido ×2 con lluvia…) × parálisis (×0.5).
- Empate: 50/50.
- **Rangos de velocidad:** el motor calcula el umbral de "rápido" como el percentil 60 del pool. El informe debe incluir una tabla de velocidades del equipo frente a las amenazas.

## Precisión y evasión
- La precisión efectiva de un movimiento es su precisión × las etapas de precisión y evasión.
- En la evaluación, **multiplica el daño esperado por la precisión**. Un 80 % falla 1 de cada 5 veces.
- Hay movimientos que nunca fallan (precisión `null`): Golpe Aéreo, Onda Voltio, Aura Esfera…
