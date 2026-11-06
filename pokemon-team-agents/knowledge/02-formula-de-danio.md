# 02 · Fórmula de daño (Gen 5+) — implementada en `tools/pkmn/damage.py`

```
Base  = floor( floor( floor(2·L/5 + 2) · Potencia · A / D ) / 50 ) + 2
Daño  = Base × Clima × Crítico × Aleatorio × STAB × Efectividad × Quemadura × Otros
```
Orden de redondeo real (el motor lo replica):
1. Clima (×1.5 o ×0.5) y crítico (×1.5), con pokeRound.
2. Aleatorio: 16 tiradas del 85 % al 100 %, con floor.
3. STAB, con pokeRound.
4. Efectividad, con floor.
5. Quemadura (×0.5 a daño físico salvo Agallas), con floor.
6. "Otros" (Vidasfera, Cinta Experto, Multiescamas, Filtro, bayas de resistencia), con pokeRound.

Validado con el ejemplo de Bulbapedia: Glaceon nv75 Colmillo Hielo vs Garchomp da 168–196.

A nivel 49: `floor(2·49/5 + 2) = 21`.

## Piezas
- **A / D:**
  - Movimiento físico: Ataque del atacante contra Defensa del rival.
  - Movimiento especial: At. Esp. contra Def. Esp.
  - Excepciones: **Psicocarga / Psicorrayo** (especial contra Defensa), **Juego Sucio** (usa el Ataque del rival), **Plancha Corporal** (usa tu Defensa).
- **STAB:** ×1.5 si el tipo del movimiento coincide con un tipo del usuario.
  - **Adaptable** lo sube a ×2.
  - **Mutatipo / Líbero** dan STAB a todo.
  - Las habilidades **-ate** (Piel Celeste, Piel Feérica, Piel Helada, Galvanizado) convierten los movimientos Normales a su tipo con ×1.2. **Si el nuevo tipo coincide con el del usuario, también reciben STAB.**
- **Efectividad:** producto de multiplicadores por cada tipo del defensor: 0, ¼, ½, 1, 2 o 4.
- **Crítico:** ×1.5. Probabilidad base 1/24 (4,17 %); +1 nivel = 1/8; +2 = 1/2; +3 = 100 %.
- **Clima:**
  - Lluvia: Agua ×1.5, Fuego ×0.5.
  - Sol: Fuego ×1.5, Agua ×0.5.
  - Arena: +50 % Def. Esp. a los tipo Roca.
  - Nieve: +50 % Defensa a los tipo Hielo. Si Añil usa granizo, en su lugar daña 1/16 a los no Hielo.
- **Multigolpe** (2–5 golpes): el motor asume 3 de media, o 5 con Encadenado. Cada golpe se calcula por separado, lo que es bueno contra Banda Focus, Robustez y Disfraz.
- **Daño fijo:** Movimiento Sísmico y Tinieblas hacen tantos PS como el nivel (49). Superdiente quita la mitad de los PS actuales.

## Cómo leer un cálculo
- `x–y%` = daño mínimo y máximo sobre los PS máximos del defensor.
- **nHKO:** golpes necesarios para debilitar.
  - "2HKO garantizado": el mínimo ≥ 50 %.
  - "posible OHKO": el máximo ≥ 100 % pero el mínimo < 100 %.
- Ten en cuenta **Restos** (+6,25 %/turno), **hazards** (Trampa Rocas: 12,5 % × efectividad de Roca) y **Vidasfera** (−10 % por golpe) al decidir si algo es 2HKO "real".

## Reglas prácticas a nivel 49 sin EVs
- Un ataque de 90 de potencia con STAB, desde un atacante de 120 de stat contra un rival neutro de ~100 PS-base/100 Def-base, hace aproximadamente un **40–48 %**.
- Por tanto: **neutro con STAB ≈ 3HKO; súper eficaz con STAB ≈ 2HKO o OHKO.** Los multiplicadores (habilidad, objeto, setup) deciden el combate.
- Un +1 (Danza Dragón, Danza Espada ×2) convierte muchos 3HKO en 2HKO y muchos 2HKO en OHKO. Por eso el setup es tan peligroso aquí.
