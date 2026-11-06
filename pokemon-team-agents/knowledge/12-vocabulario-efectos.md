# 12 · Vocabulario de efectos (contrato entre el oráculo y el motor)

Cada habilidad y objeto lleva un campo `effects`: una lista de objetos `{ "kind": ..., ... }`. El motor (`damage.py`, `setgen.py`, `teamsearch.py`) **solo entiende estos `kind`**. Todo lo demás se codifica como `note` y lo valoran los agentes con juicio.

Campo opcional común en todos: `"condition"`, con estos valores:
- `weather:rain|sun|sand|snow`
- `terrain:electric|psychic|grassy|misty`
- `low_hp` (≤ 1/3)
- `full_hp`
- `statused`
- `can_evolve`
- `moves_last`

## Ofensivos
| kind | Campos | Ejemplo |
|---|---|---|
| `stat_mult` | stat (atk/spa), mult | Potencia: `{stat:"atk", mult:2}`; Cinta Elegida ×1.5 |
| `stab_mult` | mult | Adaptable: 2 |
| `stab_all` | — | Mutatipo / Líbero |
| `power_mult` | mult, y opcionalmente max_bp, move_tag, category | Experto: `{mult:1.5, max_bp:60}`; Puño Férreo: `{mult:1.2, move_tag:"punch"}` |
| `type_power_mult` | type, mult | Carbón: Fuego ×1.2; Mar Llamas: Fuego ×1.5 con `low_hp` |
| `type_convert` | from, to, mult | Piel Celeste: Normal → Flying ×1.2 |
| `final_mult` | mult | Vidasfera 1.3; Cálculo Final: 1.3 con `moves_last` |
| `se_power_mult` | mult | Cinta Experto 1.2 |
| `nve_power_mult` | mult | Cromolente 2 |
| `max_hits` | — | Encadenado |
| `ignore_ability` | — | Rompemoldes |
| `ignore_stages` | — | Ignorante (como atacante y como defensor) |
| `ignore_burn` | — | Agallas |

## Defensivos
| kind | Campos | Ejemplo |
|---|---|---|
| `immunity` | type | Levitación: Ground; Absorbe Agua: Water; Globo Helio |
| `immunity_tag` | move_tag | Insonorizar: sound; Antibalas: bullet |
| `only_se_hits` | — | Defensa Mística |
| `incoming_type_mult` | type, mult | Sebo: Fire 0.5 e Ice 0.5; Piel Seca: Fire 1.25 |
| `incoming_se_mult` | mult | Filtro 0.75 |
| `incoming_full_hp_mult` | mult | Multiescamas 0.5 |
| `incoming_category_mult` | category, mult | Escama de Hielo: special 0.5 |
| `defense_mult` | stat (def/spd), mult | Chaleco Asalto: spd 1.5; Mineral Evolutivo: ambos con `can_evolve` |
| `resist_berry` | type | Baya Caoca: Fire |

## Velocidad y otros
| kind | Campos | Ejemplo |
|---|---|---|
| `speed_mult` | mult | Pañuelo Elegido 1.5; Nado Rápido 2 con `weather:rain` |
| `ignore_par_speed` | — | Pies Rápidos |
| `locks_move` | — | Elegidos, Monotema |
| `on_switch_in` | effect (intimidate, weather:X, terrain:X) | Intimidación, Llovizna |
| `note` | text | Cualquier efecto no calculable: Regeneración, Bromista, Robustez… |

## Reglas para el oráculo
1. Si la habilidad u objeto es **estándar** y Añil no la cambia, no hace falta escribir `effects`: el motor usa `config/efectos_estandar.json`.
2. Si Añil la **cambia** o es **nueva**, escribe `effects` explícitos en `abilities.json` o `items.json`. Esto sobrescribe el estándar.
3. Si un efecto mezcla partes calculables y no calculables, escribe ambas: los `kind` calculables y una `note` con el resto.
4. **Nunca inventes un `kind` nuevo** sin añadirlo también al motor y a este documento. Si hace falta, propónlo en `workspace/02_efectos/propuestas_motor.md`.
