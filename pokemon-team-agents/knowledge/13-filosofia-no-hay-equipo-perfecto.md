# 13 · Filosofía: no existe el equipo perfecto

> Principio del jugador, de obligado cumplimiento para todos los agentes:
> **"Nunca va a haber un equipo con cobertura perfecta ni invencible. Hay que hacer lo mejor posible con lo que hay."**

## Qué significa en la práctica
1. **El objetivo es maximizar la probabilidad de ganar, no tachar casillas.**
   - Cobertura, roles y resistencias son *medios*.
   - La métrica final es: ¿cuántas partidas gana este equipo contra rivales plausibles? Eso es lo que mide la simulación (`knowledge/14`).
2. **Un "botón" enorme vale más que una cobertura marginal.**
   - Un Pokémon con Potencia que hace OHKO a medio pool con su STAB puede valer más que uno "equilibrado" que lo cubre todo a 3HKO.
   - Dejar sin cubrir un tipo poco común es aceptable si a cambio el equipo arrolla al resto.
3. **No metas a un Pokémon flojo solo para tapar un agujero.**
   - Si el único que resiste Lucha tiene stats mediocres, a menudo es mejor aceptar la debilidad y gestionarla jugando: hazards, prioridad, ir por delante en el marcador, sacrificios.
   - El motor penaliza esto como **eslabón débil**: miembro por debajo del percentil 40 de su rol.
4. **Las debilidades se pueden compensar ofensivamente.**
   - Una debilidad compartida pesa mucho menos si el equipo tiene respuestas rápidas que golpean primero a los atacantes de ese tipo. El motor la marca como "compensada".
   - "La mejor defensa es un buen ataque" es válido cuando los números lo respaldan.
5. **Tolerancia explícita al riesgo.**
   - Toda decisión que acepte un hueco debe decir **cuánto cuesta**, por ejemplo: "perdemos contra un sweeper Lucha +2, que aparece en ~1 de cada 10 equipos según la simulación". También debe decir **qué se gana a cambio**.
   - Si el coste es bajo y la ganancia alta, se acepta.
6. **Rendimiento decreciente.**
   - La 2.ª resistencia a un tipo vale menos que la 1.ª, y la 3.ª casi nada.
   - Un 2.º check a una amenaza vale menos que el 1.º.
   - El 4.º atacante especial vale menos que el 1.er atacante físico.

## Clasificación de problemas (la usan el arquitecto y el crítico)
| Gravedad | Definición | Acción |
|---|---|---|
| **CRÍTICO** | Un arquetipo plausible (≥ 10 % de los rivales simulados, o peso ≥ 1.0) barre el equipo sin respuesta, o el winrate contra un grupo de rivales es < 35 % | Hay que arreglarlo, aunque cueste puntuación en otra parte |
| **IMPORTANTE** | Amenaza con una sola respuesta frágil, o dependencia de un movimiento < 80 % de precisión en enfrentamientos clave | Arreglar solo si el cambio no reduce el winrate global |
| **ACEPTABLE** | Hueco teórico (un tipo sin resistir, un rol sin cubrir) sin impacto medible en la simulación | Documentarlo y **no tocarlo** |

**Regla de oro:** un cambio que mejora la cobertura teórica pero **baja el winrate simulado** más allá del ruido (fuera del IC 95 %) **se rechaza**.

## Señales de que un agente se está "obcecando"
- Proponer un Pokémon de percentil bajo "porque resiste X".
- Cambiar un ataque de 120 de potencia con STAB por uno de cobertura de 60 de potencia para tocar a 1–2 tipos raros.
- Pedir resistencias a los 18 tipos.
- Rechazar un equipo con winrate más alto porque "le falta Despejar".

Cuando un agente detecte esto en otro agente, debe señalarlo citando este documento.
