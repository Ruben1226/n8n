# 05 · Habilidades: taxonomía y valoración en una partida random

> En random, **la habilidad puede pesar más que la especie**. Un Pokémon mediocre con Potencia (Huge Power) o Adaptable puede ser el mejor atacante del pool. Un muro con Ignorante, Regeneración o Muro Mágico cambia de categoría.
> Los efectos estándar codificados están en `config/efectos_estandar.json`. El **oráculo de mecánicas** debe verificar cada habilidad del fichero del jugador, porque Añil puede cambiar efectos o añadir habilidades nuevas.

## Tier S en esta partida (prioriza a sus portadores)
| Habilidad (ES / EN) | Por qué |
|---|---|
| Potencia / Huge Power, Energía Pura / Pure Power | ×2 al Ataque. Convierte a cualquiera en un atacante de élite |
| Adaptable / Adaptability | STAB ×2 (en lugar de ×1.5): +33 % a todo el daño con STAB |
| Piel Celeste/Feérica/Helada, Galvanizado (-ate) | Normal → tipo nuevo ×1.2. Velocidad Extrema, Vozarrón o Doble Filo pasan a ser STAB de prioridad o potentes, **y añaden cobertura** |
| Impulso / Speed Boost | +1 Velocidad por turno: con Protección o setup barre |
| Muro Mágico / Magic Guard | Inmune a todo daño indirecto: hazards, veneno, Vidasfera gratis |
| Regeneración / Regenerator | 33 % al cambiar: el mejor pivote defensivo |
| Ignorante / Unaware | Counter natural del setup ilimitado |
| Multiescamas / Multiscale | Mitad de daño a PS completos: setup seguro |
| Bromista / Prankster | +1 prioridad a estado: Onda Trueno, Fuego Fatuo, Mofa o pantallas primero |
| Espejo Mágico / Magic Bounce | Refleja hazards y estados |
| Sombratrampa / Shadow Tag | Atrapa y elimina counters |

## Tier A
- **Daño:**
  - Experto (Technician): ×1.5 a movimientos de potencia ≤ 60, como Puño Bala, Ultrapuño, Multiataques, Golpe Bajo, Sombra Vil.
  - Potencia Bruta (Sheer Force), con Vidasfera sin retroceso.
  - Mandíbula Fuerte, Puño Férreo, Garra Dura, Filo, Megadisparador, Temerario.
  - Cromolente (Tinted Lens): los ataques poco eficaces hacen ×2.
  - Encadenado (Skill Link): multigolpe a 5.
  - Agallas (Guts), con Llamasfera.
  - Mutatipo / Líbero.
  - Moxie, Ultraimpulso: bola de nieve.
- **Defensa:**
  - Intimidación: −1 Ataque al rival al entrar. Ojo con Competitivo y Tenacidad.
  - Sebo: resiste Fuego y Hielo.
  - Filtro / Roca Sólida: −25 % a súper eficaz.
  - Peluche (Fur Coat): ×2 Defensa.
  - Escama de Hielo: mitad de daño especial.
  - Robustez (Sturdy): sobrevive a un golpe.
  - Insonorizar.
  - Antibalas.
  - Defensa Mística / Wonder Guard: solo le dañan los súper eficaces. Muy explotable, pero brutal si el rival no tiene cobertura.
- **Inmunidades de tipo:**
  - Levitación.
  - Absorbe Agua / Fuego / Electricidad.
  - Pararrayos, Colector, Electromotor, Herbívoro.
  - Absorbe Tierra / Earth Eater.
  - Una inmunidad bien elegida **crea switch-ins gratis**.
- **Clima y campos:**
  - Llovizna, Sequía, Chorro Arena, Nevada y los Generadores de campo.
  - Habilitan núcleos con Nado Rápido, Clorofila, Ímpetu Arena, Quitanieves, Poder Solar.
  - Con 6 Pokémon, el clima solo vale si **al menos 2–3 miembros se benefician**.
- **Utilidad:**
  - Rompemoldes (ignora Levitación, Robustez, Multiescamas…).
  - Cura Natural.
  - Ojo Compuesto: hace viables Hipnosis (78 %) y Electrocañón (65 %).
  - Dicha Suerte: duplica los efectos secundarios.
  - Respondón (Contrary): Sofoco y Lluevehojas suben el stat.
  - Simple: duplica los boosts.
  - Veneno Curativo (Poison Heal), con Toxiorbe.
  - Liviano (Unburden).

## Tier negativa (penaliza a su portador)
- **Ausente (Truant):** solo actúa un turno de cada dos. Descarta salvo casos extremos.
- **Inicio Lento (Slow Start).**
- **Flaqueza (Defeatist).**
- **Rezagado (Stall).**
- **Zoquete (Klutz):** salvo con Truco.
- **Normalidad (Normalize):** salvo con un Pokémon Normal.
- **Nerviosismo y similares:** irrelevantes, cuentan como "sin habilidad".

## Cómo decide el sistema la habilidad de cada Pokémon (si tiene varias)
1. El motor genera sets para **cada** habilidad.
2. El evaluador individual compara usando la puntuación total y su propio juicio. Las habilidades `note`, no calculables, se valoran cualitativamente con la tabla de arriba.
3. El arquitecto puede elegir la habilidad que mejor encaja en el equipo, aunque no sea la mejor individualmente. Por ejemplo, Levitación para tapar una debilidad compartida a Tierra.

> **Importante:** en Pokémon Essentials, la habilidad se elige entre las posibles de la especie (normal 1/2 u oculta). Confirma con el jugador si puede **cambiar** la habilidad de un Pokémon en Añil (cápsula o parche de habilidad). Si no puede, solo vale la habilidad que tiene el ejemplar.
