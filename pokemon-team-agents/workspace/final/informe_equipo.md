# Informe final · Equipo de Ruben (Pokémon Añil, random, nivel 49)

## 1. Resumen
**Arquetipo:** ofensivo con dos sweepers de setup (Gliscor y Tinkaton, con Danza Triunfal), un mega-wallbreaker (Mega Charizard X), un revenge killer rapidísimo (Sneasler) y dos pivotes que pegan muy fuerte (Kingambit y Haxorus).

**Cómo gana:** Sneasler pone Púas y presiona. Mega Charizard X y Kingambit abren huecos. Gliscor (o Tinkaton) hace Danza Triunfal en un turno seguro y barre al final.

| | Resultado simulado (motor oficial de Showdown, 1.120 partidas contra rivales nuevos) |
|---|---|
| **Global** | **75,0 %** (IC 95 %: 72,4–77,4 %) |
| Contra equipos hechos con tu propio pool (lo más parecido a tus colegas) | **96,3 %** |
| Contra equipos competitivos aleatorios de Showdown (con legendarios) | 66,5 % |

> El porcentaje mide la **calidad relativa** del equipo con un bot que juega bien pero sin faroles. No es tu winrate real contra humanos. Sí garantiza que este equipo ganó a todas las alternativas probadas.

**Cómo se eligió:**
1. 1.196 sets candidatos.
2. Algoritmo genético (5 búsquedas) → 14 finalistas.
3. Simulación de los finalistas.
4. Refinado hueco a hueco.
5. Confirmación con dos conjuntos de rivales nuevos.

La Mega X subía unos 8 puntos frente al mismo equipo sin ella. Cambiar Haxorus-atacante y Golisopod por Tinkaton y Haxorus-soporte subió otros ~6 puntos, confirmado en dos validaciones independientes.

## 2. El equipo (pegar en Showdown → Teambuilder → Import)
```
Charizard @ Charizardite X
Ability: Flower Gift
Level: 49
Hardy Nature
IVs: 29 HP / 16 Atk / 13 Def / 16 SpA / 3 SpD / 6 Spe
- Armor Cannon
- Aqua Step
- Zippy Zap
- Hammer Arm

Gliscor @ Sky Plate
Ability: Shadow Shield
Level: 49
Adamant Nature
IVs: 14 HP / 8 Atk / 26 Def / 1 SpA / 18 SpD / 26 Spe
- Victory Dance
- Headlong Rush
- Dual Wingbeat
- Zippy Zap

Tinkaton @ Life Orb
Ability: Multiscale
Level: 49
Impish Nature
IVs: 12 HP / 17 Atk / 11 Def / 10 SpA / 23 SpD / 16 Spe
- Victory Dance
- Magical Torque
- Wave Crash
- Spin Out

Sneasler @ Payapa Berry
Ability: Compound Eyes
Level: 49
Serious Nature
IVs: 2 HP / 24 Atk / 12 Def / 23 SpA / 30 SpD / 26 Spe
- Spikes
- Parting Shot
- Combat Torque
- Wave Crash

Kingambit @ Air Balloon
Ability: Neuroforce
Level: 49
Lonely Nature
IVs: 0 HP / 9 Atk / 21 Def / 21 SpA / 3 SpD / 12 Spe
- Parting Shot
- Glare
- Spin Out
- Wicked Blow

Haxorus @ Covert Cloak
Ability: Shadow Shield
Level: 49
Relaxed Nature
IVs: 25 HP / 0 Atk / 20 Def / 13 SpA / 1 SpD / 20 Spe
- Strength Sap
- Court Change
- Magical Torque
- Land's Wrath
```
Recuerda: **0 EVs** en todos.

### Rol de cada miembro
| Pokémon | Rol | Por qué está | Nunca dejarlo contra… |
|---|---|---|---|
| **Mega Charizard X** (Fuego/Dragón, Garra Dura) | Wallbreaker mixto | 130/130 en ataques. Garra Dura potencia Danza Acuática, Pikaturbo (con prioridad) y Machada. Cañón Armadura como golpe especial. Resiste Agua, Fuego, Planta y Eléctrico | Atacantes de Tierra o Roca rápidos (Arremetida de Mamoswine le hace 146–175 %) |
| **Gliscor** (Tierra/Volador, Guardia Espectro) | **Condición de victoria principal** (1.906 KOs en la simulación: el MVP) | Guardia Espectro reduce a la mitad el daño a PS completos, así que la Danza Triunfal sale segura. Arremetida es STAB brutal: hace KO directo a Nidoking, Delphox y Typhlosion-H | Agua e Hielo (Envite Acuático de Mamoswine le hace 91–107 %) |
| **Tinkaton** (Hada/Acero, Multiescamas) | 2.ª condición de victoria | Multiescamas + Danza Triunfal. Tipos defensivos excelentes. Feerichoque deja KO a Zoroark | Fuego y Tierra fuertes |
| **Sneasler** (Lucha/Veneno) | Lead, Púas, revenge killer | El más rápido del pool (135). Combat Torque y Envite Acuático dejan KO a medio pool. Última Palabra para pivotar debilitando al rival | Cualquier golpe fuerte: es frágil. Psíquico ×4 (lleva Baya Payapa) |
| **Kingambit** (Siniestro/Acero, Fuerza Cerebral) | Wallbreaker lento y pivote | Golpe Mordaz (siempre crítico) y Quemarrueda con STAB; Fuerza Cerebral añade +25 % a los súper eficaces. Deslumbrar paraliza. El Globo lo hace inmune a Tierra mientras no le golpeen | Lucha (×4) |
| **Haxorus** (Dragón, Guardia Espectro) | Pivote defensivo y control | Absorbefuerza (cura y baja el Ataque del rival), Cambio de Cancha (te quita las trampas y se las da al rival), Feerichoque y Fuerza Telúrica | Hada, Hielo y Dragón especiales |

## 3. Preparación en el juego (checklist)
- [ ] **Menta Firme → Gliscor** (pasa de Modesta a Firme). La Menta Mansa no hace falta.
- [ ] **Mini Setas (2 de 7)** con la Experta en Habilidades:
  - Tinkaton: Raíz robusta → **Multiescamas**.
  - Haxorus: Cálculo Final → **Guardia Espectro**.
  - Charizard, Sneasler y Kingambit (Fuerza Cerebral) conservan la suya.
- [ ] **Objetos:** Charizardita X (con Megaaro), Placa Cielo, Vidasfera, Baya Payapa, Globo Helio, Capa Furtiva.
- [ ] **Movimientos:**
  - **Charizard:** Cañón Armadura (Recordador), Danza Acuática (MT26), Pikaturbo (MT23), Machada (MT62).
  - **Gliscor:** Danza Triunfal (MT86), Arremetida (MT93), Pikaturbo (MT23). Doble Ala ya lo sabe.
  - **Tinkaton:** Danza Triunfal (MT86), Feerichoque (MT77), Envite Acuático (MT63), Quemarrueda (MT28).
  - **Sneasler:** Última Palabra (MT31), Envite Acuático (MT63). Púas y Combat Torque ya los sabe.
  - **Kingambit:** Deslumbrar (Recordador), Quemarrueda (MT28). Última Palabra y Golpe Mordaz ya los sabe.
  - **Haxorus:** Absorbefuerza, Cambio de Cancha y Fuerza Telúrica (Recordador), Feerichoque (MT77).
- [ ] Kingambit y Haxorus están en la Caja 50; Charizard, Tinkaton y Sneasler en la Caja 1; Gliscor en la Caja 2.

## 4. Velocidades (nivel 49, IVs y naturaleza reales)
| Tu equipo | Vel. | Amenazas de tu pool que te superan o empatan |
|---|---|---|
| Sneasler | 135 | Ninguna (empata con otro Sneasler) |
| Gliscor | 110 | Talonflame 133, Delphox 130, Kilowattrel 124, Zoroark 123, Floatzel 121, Basculin 111 |
| Mega Charizard X | 105 | Las anteriores + Haxorus 109 |
| Tinkaton | 104 | Ídem. **Tras una Danza Triunfal (+1) supera a todo tu pool** |
| Haxorus | 98 | — |
| Kingambit | 59 | Casi todos: juega a recibir y devolver |

Pikaturbo (Charizard y Gliscor) tiene **prioridad +2**: remata a los rápidos.

Más cálculos, miembro a miembro, en `workspace/final/calculos.md`. Ojo: la calculadora rápida no aplica el crítico garantizado de Golpe Mordaz; el daño real es ~1,5× el mostrado.

## 5. Plan de juego
- **Lead:** Sneasler.
  - Contra un lead lento: **Púas**.
  - Contra uno frágil y más lento: atácalo (Combat Torque o Envite Acuático).
  - Si te amenaza: **Última Palabra** para meter gratis a Gliscor o Charizard.
- **Medio juego:**
  - Mega Charizard X y Kingambit rompen muros.
  - Haxorus entra contra atacantes físicos: Absorbefuerza le cura y les baja el Ataque.
  - Si el rival pone trampas, **Cambio de Cancha** se las devuelve.
- **Cierre:** con sus counters (Agua, Hielo, prioridad fuerte) debilitados o tocados, mete a **Gliscor**, haz **Danza Triunfal** con Guardia Espectro intacta y barre con Arremetida, Doble Ala y Pikaturbo. Tinkaton es el plan B con Multiescamas.
- **Contra setup rival:** Kingambit (Golpe Mordaz ignora sus subidas de Defensa, por ser crítico), Deslumbrar (parálisis), Absorbefuerza (baja su Ataque) y la prioridad de Pikaturbo.
- **Cláusula de sueño:** no llevas movimientos de sueño; nada que gestionar.

## 6. Riesgos aceptados (no existe el equipo perfecto)
- **Lluvia o equipos de Agua muy ofensivos y atacantes especiales legendarios** (Kyogre, Miraidon, Palkia): son los que más partidas nos ganan en simulación. El equipo es sobre todo físico y Gliscor sufre contra Agua y Hielo.
  - Se acepta porque contra equipos como los de tu pool apenas pierde (96,3 %), y cambiarlo costaba winrate global en todas las pruebas.
  - **En juego:** guarda a Mega Charizard X (resiste Agua) y a Haxorus para ese rival; no expongas a Gliscor pronto.
- **Debilidad compartida a Lucha** (Kingambit ×4 y Tinkaton ×2): Gliscor y Charizard la resisten o es neutra, y Sneasler la frena primero.
- **IVs bajos en algunos stats** (Haxorus 0 en Ataque, Kingambit 0 en PS): están incluidos en todos los cálculos y simulaciones.

## 7. Alternativas (simuladas con los mismos rivales, tras la corrección de Realeza)
| Equipo | Winrate |
|---|---|
| **Este** (Mega X, Gliscor, Tinkaton, Sneasler, Kingambit, Haxorus) | **81,2 %** |
| Tinkaton, Haxorus, Kingambit, Mega X, Nidoking, Golisopod | 70,6 % |
| Mega X, Mamoswine, Sneasler, Kingambit, Golisopod, Haxorus | 68,5 % |
| Haxorus, Golisopod, Tinkaton, Mamoswine, Mega X, Kingambit | 68,0 % |

Las variantes sin megaevolución quedan entre 5 y 10 puntos por debajo de su versión con Mega X.

## 8. Supuestos y dudas
- **Combates en Showdown Custom Game ⇒ mandan los tipos y stats OFICIALES de Showdown**, no los de Añil. En Showdown, por ejemplo, Samurott es Agua pura y Meganium Planta pura. Si jugáis con un servidor con datos de Añil, avísame y se recalcula (`datos_especie: "anil"`).
- **Habilidades exclusivas de Añil, que no existen en Showdown** (Realeza, Poder Gélido, Coleóptero, Raíz robusta, Camorrista, Poder Sabio, Tintineo, Inflamable): se tratan como "sin efecto" y se evitan. Corregido: en una versión anterior se supuso Realeza = Adaptable; tras quitarlo se rehízo todo el proceso y este equipo volvió a salir primero (81 % frente al 71 % del siguiente).
- **Objetos:** solo los de tu mochila (no tienes Restos ni objetos Elegidos). Si en Showdown podéis usar cualquier objeto, el equipo mejoraría y conviene recalcularlo.
- Los movimientos Deslizamiento y Escalofrío no existen en Showdown y se descartaron.
