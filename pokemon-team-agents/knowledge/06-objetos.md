# 06 · Objetos

> Solo cuentan los objetos que el jugador **tiene**, con su cantidad (`items.json → quantity`). El motor penaliza usar más unidades de las disponibles.

## Ofensivos
| Objeto (ES / EN) | Efecto | Cuándo |
|---|---|---|
| Cinta Elegida / Choice Band | ×1.5 Ataque, bloqueado en un movimiento | Wallbreaker físico con buena cobertura |
| Gafas Elegidas / Choice Specs | ×1.5 At. Esp., bloqueado | Wallbreaker especial |
| Pañuelo Elegido / Choice Scarf | ×1.5 Velocidad, bloqueado | Revenge killer. Supera en velocidad a sweepers rivales |
| Vidasfera / Life Orb | ×1.3 al daño, −10 % PS por golpe | Sweepers con setup o atacantes mixtos que necesitan cambiar de movimiento |
| Cinta Experto / Expert Belt | ×1.2 a súper eficaces | Atacantes con mucha cobertura que no quieren retroceso |
| Potenciadores de tipo (Carbón, Agua Mística, Imán…) | ×1.2 a un tipo | Sin otra opción mejor: ×1.2 al STAB principal sin desventajas |
| Cinta Fuerte / Gafas Especiales | ×1.1 físico / especial | Relleno |
| Banda Focus / Focus Sash | Sobrevive a 1 PS desde PS completos | Leads frágiles con hazards, o sweepers frágiles con setup |
| Seguro Debilidad / Weakness Policy | +2 Atq y At. Esp. al recibir un súper eficaz | Sweepers bulky con pocas debilidades |
| Hierba Blanca / White Herb | Restaura bajadas una vez | Rompecoraza, Sofoco |

## Defensivos y de utilidad
| Objeto | Efecto | Cuándo |
|---|---|---|
| Restos / Leftovers | +1/16 PS por turno | Muros, pivotes, setup bulky. **El más versátil** |
| Lodo Negro / Black Sludge | Igual que Restos para tipos Veneno | — |
| Mineral Evolutivo / Eviolite | ×1.5 Def y Def. Esp. **si puede evolucionar** | **Muy fuerte antes del 5.º gimnasio**: hay muchos Pokémon sin evolucionar del todo |
| Chaleco Asalto / Assault Vest | ×1.5 Def. Esp., solo ataques | Atacantes bulky sin movimientos de estado |
| Casco Dentado / Rocky Helmet | 1/6 al atacante por contacto | Muros físicos |
| Botas Gruesas / Heavy-Duty Boots | Inmune a hazards | Pokémon débiles a Roca que cambian mucho |
| Baya Zidra / Sitrus Berry | +25 % bajo el 50 % | Alternativa común si no hay Restos |
| Baya Ziuela / Lum Berry | Cura un estado | Setup contra Fuego Fatuo, Onda Trueno o sueño |
| Bayas de resistencia (Caoca, Pasio…) | Reduce a la mitad un súper eficaz | Sobrevivir a un golpe concreto que te deja KO |
| Globo Helio / Air Balloon | Inmune a Tierra hasta recibir un golpe | — |
| Toxiorbe / Llamasfera | Envenena o quema al portador | Con Veneno Curativo, Agallas, Piel Milagro |
| Refleluz / Light Clay | Pantallas duran 8 turnos | Lead de pantallas |

## Reglas de asignación (las aplica primero el motor y luego las revisa el arquitecto)
1. **Objetos únicos al mejor portador posible.** Si solo hay un Restos, va al Pokémon que más turnos pase en el campo.
2. **Mineral Evolutivo:** comprueba `can_evolve = true`. A nivel 49 es el objeto defensivo más fuerte del juego.
3. **Elegidos (Cinta, Gafas, Pañuelo):** el set debe tener 3–4 ataques útiles y cobertura. Nunca con movimientos de estado salvo Truco.
4. **Vidasfera:** no con Pokémon que dependan de recuperación pasiva. Sí con Muro Mágico, porque no pierde PS.
5. **Sin objeto** solo si se agotan los disponibles. Un objeto mediocre es mejor que ninguno.
6. **Cláusula de objeto:** no está en vigor. Pueden repetirse si hay unidades suficientes.
