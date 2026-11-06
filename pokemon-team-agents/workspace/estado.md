# Estado del pipeline (partida de Ruben, 4 medallas, nivel 49)

## Supuestos y decisiones
- **Datos de especie = Showdown oficial.** El fichero indica que los combates son en Showdown [Gen 9] Custom Game, que usa tipos y stats oficiales. Los de Añil se conservan como `types_anil` / `base_stats_anil`. Afecta sobre todo a Samurott (Agua en Showdown, Agua/Lucha en Añil), Meganium (Planta vs Planta/Hada), Misdreavus (Fantasma vs Fantasma/Hada) y a pequeñas diferencias de stats.
- **Realeza (Kingambit) = Adaptability**, porque así la exporta el exportador a Showdown.
- **Habilidades exclusivas de Añil sin equivalente en Showdown** se tratan como sin efecto y se evitan: Poder Gélido, Coleóptero, Raíz robusta, Camorrista, Poder Sabio, Tintineo, Inflamable.
- **Movimientos de Añil inexistentes en Showdown** se descartan: DESLIZAMIENTO, ESCALOFRIO.
- **Mentas concretas:** 1 Mansa (Quiet) y 1 Firme (Adamant).
- **Mini Setas:** 7 (cambio de habilidad dentro de las posibles de la especie).
- **Megaevolución:** Charizardita X + Megaaro → entrada Charizard-Mega-X.
- **Objetos:** solo los de la mochila, respetando cantidades (1 Vidasfera, sin Restos ni Elegidos).
- **Nivel por Pokémon:** el real de la partida (Furfrou 45, el resto 49).

## Fases
1. Ingesta: OK (`convertir.py`; 46 entradas, 520 movimientos, 92 habilidades, 111 objetos; `validar` = OK).
2. Oráculo: efectos de 43 habilidades del pool codificados; placas, gemas y Dado Trucado añadidos.
3. Sets: 1196 sets candidatos.
4. Amenazas: 30 del pool + 54 genéricas; matriz de 700 candidatos.
5. GA: 3 semillas + núcleos (Charizard, Delphox) → 14 finalistas simulados.
   - Mejor: F0MEGA, 73,4 %. La mega sube unos 8 puntos frente al mismo equipo sin ella.
   - Calibración: Spearman 0,672 → 0,679, no se adoptan pesos nuevos. Componente más predictivo: presión ofensiva.
   - **Fallo del simulador detectado y corregido** (elecciones forzadas a 'movimiento 1' al cerrar turno). Bot recalibrado: 95 % contra bot aleatorio. Finalistas re-simulados → mejor F1MEGA, 78,4 %.
   - Refinado de F1MEGA: Haxorus-atacante → Tinkaton (Multiscale, setup). Validación con rivales nuevos: 65,7 → 68,4 %.
   - Decisión con dos semillas nuevas: variante C (refinado + Haxorus-soporte en lugar de Golisopod) gana a todas (71,4 % y 69,0 %).
6. Mentas: la Firme va a Gliscor (incluida en el set). La Mansa no aporta. Otras asignaciones simuladas: sin diferencia.
   Objetos: Placa Cielo en Gliscor (+1,4) en lugar del Dado Trucado, inútil con Doble Ala. Sneasler mantiene Ojo Compuesto (ahorra una Mini Seta).
7. Crítico: las derrotas vienen de equipos de lluvia/agua y de atacantes especiales legendarios → riesgo aceptado y documentado.
8. Informe: `workspace/final/informe_equipo.md`, `equipo_showdown.txt`, `calculos.md`. Simulación final: 76,9 % (1.120 partidas; 99,4 % contra el pool).

## Corrección (indicada por el jugador): Realeza NO existe en Showdown
- Ya no se mapea a Adaptability: Realeza pasa a "sin efecto". Efectos de habilidades del pool movidos a `config/efectos_estandar.json` para que sobrevivan a reconversiones.
- Pipeline rehecho: sets (1182) → matriz → GA (3 semillas + núcleos) → 20 finalistas simulados.
- El equipo anterior con **Kingambit en Fuerza Cerebral** (habilidad actual, sin Mini Seta) sigue primero: 81,2 % frente a 70,6 % del siguiente. El refinado no encuentra mejoras.
- Simulación final de informe (mismos rivales que antes): 75,0 % (antes 76,9 % con Adaptability), 96,3 % contra el pool.
- Ruido medido: el mismo equipo contra sí mismo en dos procesos da ±2–3 puntos. Por eso los cambios exigen mejorar con varias semillas.
