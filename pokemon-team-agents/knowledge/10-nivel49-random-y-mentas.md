# 10 · Particularidades: nivel 49, 0 EVs, random y mentas

## Nivel 49 / 0 EVs
- **Stats comprimidos:** un Pokémon de base 130 en Velocidad tiene 148 (neutro) o 162 (+). Uno de base 100 tiene 115 o 126.
- **Velocidad:**
  - La naturaleza +Vel (≈ +10–16 puntos) supera a cualquiera que tenga hasta unos 12 puntos de base más que tú con naturaleza neutra.
  - **Los empates y "casi empates" son frecuentes.**
  - **Tabla de velocidades obligatoria en el informe.**
- **IVs:** sin EVs, la diferencia entre IV 31 y IV 0 es de ~15 puntos a nivel 49, más que una naturaleza. Si el jugador conoce los IVs, inclúyelos. Si un IV de Velocidad es bajo, puede cambiar el rol (por ejemplo, a Espacio Raro).
- **Mineral Evolutivo:** antes del 5.º gimnasio, muchos Pokémon en `can_evolve = true` (Porygon, Chansey, Scyther, Dusclops, Rhydon-like…) son muros excelentes con él.
- **Daño fijo** (Movimiento Sísmico / Tinieblas): 49 PS. Muy fuerte en muros con Mineral Evolutivo.
- **Movimientos disponibles:**
  - Solo cuentan los aprendidos por nivel hasta el 49, el Recordador (en Añil hay uno en cada Centro Pokémon), las MTs poseídas y los tutores accesibles.
  - **Los movimientos de nivel > 49 NO están disponibles.**

## Random
- **El fichero del jugador manda.** Ningún agente debe "corregir" un learnset o una habilidad por parecer raro.
- **Busca outliers positivos:**
  - Habilidad tier S en un Pokémon con stats decentes.
  - Movimiento de STAB fuerte o de prioridad poco habitual.
  - Setup + habilidad de velocidad.
  - Cobertura completa.
- **Busca combos:** -ate + Velocidad Extrema, Experto + multigolpe, Potencia Bruta + Vidasfera, Agallas + Llamasfera, Veneno Curativo + Toxiorbe, Respondón + Sofoco o Lluevehojas, Encadenado + Bala Semilla o Carámbano, Muro Mágico + Vidasfera, Simple + setup.
- **El pool rival sale del mismo randomizer.** Por eso tus Pokémon más fuertes son un buen modelo de lo que te puedes encontrar (`pool_threats`).
- Los **arquetipos genéricos por tipo** (`generic_threats`: un atacante físico, uno especial y un muro por cada tipo) aseguran que el equipo no tenga agujeros de cobertura contra nada.

## Mentas (recurso limitado)
Las asigna el agente `asesor-naturalezas`. **Algoritmo:**
1. Para cada miembro del equipo final, compara su set con la naturaleza actual y con la ideal:
   - Velocidad: ¿cambia algún enfrentamiento de velocidad clave?
   - Daño: ¿convierte algún 3HKO en 2HKO, o un 2HKO en OHKO, contra amenazas importantes?
   - Aguante: ¿sobrevive a algún golpe clave?
2. **Ganancia marginal** = nº de enfrentamientos de la matriz que cambian (de perder a ganar el check o counter), ponderado por el peso de la amenaza.
3. Ordena por ganancia y asigna las N mentas a los mayores. Si un miembro ya tiene una naturaleza útil (por ejemplo, Alegre en un atacante físico rápido), puede no necesitar menta.
4. Las naturalezas neutras (Fuerte, Seria…) y las que bajan un stat que usas son las prioritarias para recibir menta.
5. **Nunca gastes mentas en Pokémon que no estén en el equipo final.**
6. Informa de la alternativa: "si consigues 1 menta más, dásela a X por Y".
