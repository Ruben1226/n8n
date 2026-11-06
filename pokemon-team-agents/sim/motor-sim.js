'use strict';
/**
 * Motor de simulación: usa el motor OFICIAL de batalla de Pokémon Showdown (pokemon-showdown)
 * y la calculadora oficial (@smogon/calc) para que dos bots heurísticos jueguen partidas 6vs6.
 *
 * - Aplica los cambios de Añil (tipos y stats base) mutando las especies en memoria.
 * - Formato: gen9customgame + Sleep Clause Mod + Species Clause, nivel 49, 0 EVs.
 * - El bot es OMNISCIENTE (ve el equipo rival completo): no es un jugador humano, es un
 *   instrumento de medida. Ambos bandos usan el mismo bot, así que la comparación es justa.
 */
const {Dex, Battle, Teams} = require('pokemon-showdown');
const calc = require('@smogon/calc');

const GEN = calc.Generations.get(9);

// Habilidad exclusiva de Añil "Realeza": x1.5 a los ataques que NO son del tipo del usuario.
// En Showdown el jugador la emula sin habilidad y eligiendo un movimiento de más potencia; aquí se
// registra como habilidad propia para simularla con exactitud.
Dex.data.Abilities.realeza = {
  name: 'Realeza', num: 90001, rating: 3.5, flags: {},
  onBasePowerPriority: 23,
  onBasePower(basePower, source, target, move) {
    if (move.category !== 'Status' && !source.hasType(move.type)) return this.chainModify(1.5);
  },
};
Dex.abilities.abilityCache.clear();
Dex.abilities.allCache = null;
// Parámetros del bot (ajustados por barrido contra la versión base; ver knowledge/14)
const P = {switchKO: 0.65, badMatchup: 0.3, badMatchupDealt: 0.22, setupSafety: 1.5};
const fs = require('fs');
const path = require('path');
let REGLAS = {};
try { REGLAS = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'reglas.json'), 'utf8')); } catch (e) {}
const FORMAT = 'gen9customgame@@@Sleep Clause Mod,Species Clause,OHKO Clause,Evasion Moves Clause' +
  (REGLAS.modo_inverso ? ',Inverse Mod' : '');
const toID = s => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

// ---------------------------------------------------------------- datos de Añil
const TYPE_EN = {normal: 'Normal', fire: 'Fire', fuego: 'Fire', water: 'Water', agua: 'Water', electric: 'Electric',
  electrico: 'Electric', grass: 'Grass', planta: 'Grass', ice: 'Ice', hielo: 'Ice', fighting: 'Fighting', lucha: 'Fighting',
  poison: 'Poison', veneno: 'Poison', ground: 'Ground', tierra: 'Ground', flying: 'Flying', volador: 'Flying',
  psychic: 'Psychic', psiquico: 'Psychic', bug: 'Bug', bicho: 'Bug', rock: 'Rock', roca: 'Rock', ghost: 'Ghost',
  fantasma: 'Ghost', dragon: 'Dragon', dark: 'Dark', siniestro: 'Dark', steel: 'Steel', acero: 'Steel', fairy: 'Fairy', hada: 'Fairy'};
const normType = t => TYPE_EN[toID(t.normalize('NFD').replace(/[̀-ͯ]/g, ''))] || t;

/** Aplica tipos y stats base de Añil (pokemon.json) a las especies de Showdown. Devuelve avisos. */
function applyAnilSpecies(pokemonList) {
  // Las especies de Showdown están congeladas: se modifican los DATOS crudos y se vacía la caché.
  const warnings = [];
  for (const p of pokemonList || []) {
    const sdName = p.showdown_name || p.name;
    const sp = Dex.species.get(sdName);
    if (!sp.exists) { warnings.push(`Especie desconocida para Showdown: ${sdName} (añade showdown_name)`); continue; }
    const raw = Dex.data.Pokedex[sp.id];
    if (!raw) continue;
    if (p.base_stats) {
      const b = p.base_stats;
      raw.baseStats = {hp: b.hp, atk: b.atk, def: b.def, spa: b.spa, spd: b.spd, spe: b.spe};
    }
    if (p.types && p.types.length) raw.types = p.types.map(normType);
  }
  Dex.species.speciesCache.clear();
  return warnings;
}

const NATURE_EN = {fuerte: 'Hardy', hurana: 'Lonely', audaz: 'Brave', firme: 'Adamant', picara: 'Naughty', osada: 'Bold',
  docil: 'Docile', placida: 'Relaxed', agitada: 'Impish', floja: 'Lax', miedosa: 'Timid', activa: 'Hasty', seria: 'Serious',
  alegre: 'Jolly', ingenua: 'Naive', modesta: 'Modest', afable: 'Mild', mansa: 'Quiet', timida: 'Bashful', alocada: 'Rash',
  serena: 'Calm', amable: 'Gentle', grosera: 'Sassy', cauta: 'Careful', rara: 'Quirky'};
const normNature = n => {
  if (!n) return 'Serious';
  const k = toID(n.normalize('NFD').replace(/[̀-ͯ]/g, ''));
  return NATURE_EN[k] || (Dex.natures.get(n).exists ? Dex.natures.get(n).name : 'Serious');
};

/** Convierte un set del motor Python a PokemonSet de Showdown. Usa los campos showdown_* si existen. */
function toShowdownSet(s, level = 49, warnings = null) {
  if (warnings) {
    const ab = s.showdown_ability || s.ability;
    if (ab && !Dex.abilities.get(ab).exists) warnings.push(`${s.species}: habilidad '${ab}' no existe en Showdown (añade showdown_ability con la más parecida)`);
    const it = s.showdown_item || s.item;
    if (it && !Dex.items.get(it).exists) warnings.push(`${s.species}: objeto '${it}' no existe en Showdown (añade showdown_item)`);
  }
  const moveMap = s.showdown_moves || {};
  const moves = (s.moves || []).map(m => moveMap[m] || m).filter(m => Dex.moves.get(m).exists);
  const ivs = Object.assign({hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31}, s.ivs || {});
  return {
    name: s.nickname || s.species, species: s.showdown_species || s.species,
    ability: s.showdown_ability || s.ability || 'No Ability',
    item: s.showdown_item || s.item || '', nature: normNature(s.nature), gender: '',
    evs: {hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0}, ivs, level: s.level || level, moves,
  };
}

/** Equipo "random de otro jugador": generador oficial de Random Battle, normalizado a nv49 y 0 EVs. */
function randomForeignTeam(level = 49, seed = null) {
  const opts = seed === null ? null : {seed: [seed, seed + 11, seed + 23, seed + 37]};
  return Teams.generate('gen9randombattle', opts).map(s => ({
    ...s, level, evs: {hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0},
    ivs: {hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31}, teraType: undefined,
  }));
}

// ---------------------------------------------------------------- cálculo de daño (cacheado)
const WEATHER = {raindance: 'Rain', primordialsea: 'Heavy Rain', sunnyday: 'Sun', desolateland: 'Harsh Sunshine',
  sandstorm: 'Sand', hail: 'Hail', snow: 'Snow', snowscape: 'Snow'};
const TERRAIN = {electricterrain: 'Electric', grassyterrain: 'Grassy', psychicterrain: 'Psychic', mistyterrain: 'Misty'};
const STATUS = {brn: 'brn', par: 'par', psn: 'psn', tox: 'tox', slp: 'slp', frz: 'frz'};

function calcMon(p) {
  const opts = {
    level: p.level, ability: p.ability ? Dex.abilities.get(p.ability).name : undefined,
    item: p.item ? Dex.items.get(p.item).name : undefined, nature: p.set.nature,
    ivs: p.set.ivs, evs: p.set.evs, boosts: {...p.boosts}, status: STATUS[p.status] || '',
    curHP: p.hp, overrides: {types: p.getTypes ? p.getTypes() : p.species.types, baseStats: p.species.baseStats},
  };
  try { return new calc.Pokemon(GEN, p.species.name, opts); } catch (e) {
    try { return new calc.Pokemon(GEN, p.species.baseSpecies, opts); } catch (e2) { return null; }
  }
}

function fieldOf(battle) {
  return new calc.Field({weather: WEATHER[battle.field.weather] || undefined, terrain: TERRAIN[battle.field.terrain] || undefined});
}

const cache = new Map();
/** Daño esperado en fracción de los PS ACTUALES del defensor (0..∞), ya ponderado por precisión. */
function expectedDamage(battle, att, def, moveId) {
  const move = Dex.moves.get(moveId);
  if (!move.exists || move.category === 'Status') return 0;
  const key = [battle.field.weather, battle.field.terrain, att.species.id, att.ability, att.item, JSON.stringify(att.boosts),
    att.status, def.species.id, def.ability, def.item, JSON.stringify(def.boosts), def.status, def.hp, moveId].join('|');
  if (cache.has(key)) return cache.get(key);
  let frac = 0;
  try {
    const a = calcMon(att), d = calcMon(def);
    if (a && d) {
      const r = calc.calculate(GEN, a, d, new calc.Move(GEN, move.name), fieldOf(battle));
      const dmg = r.damage;
      // multigolpe: la calculadora devuelve una lista de tiradas POR GOLPE -> sumar golpes tirada a tirada
      const arr = Array.isArray(dmg) ? (Array.isArray(dmg[0]) ? dmg[0].map((_, i) => dmg.reduce((s, hit) => s + hit[i], 0)) : dmg) : [dmg];
      const avg = arr.reduce((s, v) => s + v, 0) / arr.length;
      const acc = move.accuracy === true ? 1 : move.accuracy / 100;
      frac = (avg * acc) / Math.max(1, def.hp);
      // @smogon/calc no conoce Realeza: se corrige a mano
      if (toID(att.ability) === 'realeza' && !att.getTypes().includes(move.type)) frac *= 1.5;
    }
  } catch (e) { frac = 0; }
  if (cache.size > 200000) cache.clear();
  cache.set(key, frac);
  return frac;
}

function bestDamage(battle, att, def, movesIds) {
  let best = {id: null, frac: 0, priority: 0};
  for (const id of movesIds) {
    const f = expectedDamage(battle, att, def, id);
    if (f > best.frac) best = {id, frac: f, priority: Dex.moves.get(id).priority};
  }
  return best;
}

const TRACE = {last: ''};
const BOOST = b => (b >= 0 ? (2 + b) / 2 : 2 / (2 - b));
/** Stat "en bruto" sin disparar eventos del simulador (getStat ejecuta habilidades y puede romper). */
function rawStat(p, stat) {
  return Math.floor(p.storedStats[stat] * BOOST(p.boosts[stat] || 0));
}
const WEATHER_SPEED = {swiftswim: ['raindance', 'primordialsea'], chlorophyll: ['sunnyday', 'desolateland'],
  sandrush: ['sandstorm'], slushrush: ['hail', 'snow', 'snowscape']};
function speedOf(battle, p) {
  let s = rawStat(p, 'spe');
  const ab = toID(p.ability), it = toID(p.item);
  if (it === 'choicescarf') s *= 1.5;
  if (WEATHER_SPEED[ab] && WEATHER_SPEED[ab].includes(battle.field.weather)) s *= 2;
  if (ab === 'quickfeet' && p.status) s *= 1.5;
  else if (p.status === 'par') s *= 0.5;
  if (p.side.sideConditions.tailwind) s *= 2;
  if (battle.field.pseudoWeather.trickroom) s = 10000 - s;
  return Math.floor(s);
}

// ---------------------------------------------------------------- bot heurístico
const SETUP = new Set(['swordsdance', 'dragondance', 'nastyplot', 'calmmind', 'quiverdance', 'bulkup', 'shellsmash',
  'shiftgear', 'agility', 'coil', 'irondefense', 'cosmicpower', 'curse', 'tailglow', 'victorydance', 'tidyup', 'workup',
  'growth', 'honeclaws', 'rockpolish', 'autotomize', 'geomancy', 'clangoroussoul', 'filletaway', 'bellydrum']);
const HAZARDS = {stealthrock: 'stealthrock', spikes: 'spikes', toxicspikes: 'toxicspikes', stickyweb: 'stickyweb'};
const REMOVAL = new Set(['rapidspin', 'defog', 'mortalspin', 'tidyup', 'courtchange']);
const RECOVERY = new Set(['recover', 'roost', 'softboiled', 'slackoff', 'moonlight', 'morningsun', 'synthesis', 'milkdrink',
  'shoreup', 'strengthsap', 'wish', 'rest', 'healorder', 'lifedew', 'junglehealing']);

function oppOf(side) { return side.foe; }

function statusMoveValue(battle, me, opp, move, oppBestOnMe) {
  const id = move.id;
  if (opp.status || opp.volatiles.substitute) return 0;
  const types = opp.getTypes();
  if (id === 'willowisp') return (!types.includes('Fire') && rawStat(opp, 'atk') > rawStat(opp, 'spa') && toID(opp.ability) !== 'guts') ? 0.6 : 0;
  if (['thunderwave', 'glare', 'stunspore', 'nuzzle'].includes(id)) {
    if (id === 'thunderwave' && (types.includes('Electric') || types.includes('Ground'))) return 0;
    return speedOf(battle, opp) > speedOf(battle, me) ? 0.55 : 0.2;
  }
  if (id === 'toxic') return (!types.includes('Poison') && !types.includes('Steel')) ? 0.45 : 0;
  if (['spore', 'sleeppowder', 'hypnosis', 'sing', 'lovelykiss', 'darkvoid', 'yawn', 'grasswhistle'].includes(id)) {
    const sleeping = opp.side.pokemon.some(p => p.status === 'slp' && !p.fainted);
    if (sleeping) return 0; // cláusula de sueño
    const acc = move.accuracy === true ? 1 : move.accuracy / 100;
    return 0.9 * acc;
  }
  return 0;
}

/** Elige la acción para un Pokémon activo. Devuelve string de elección de Showdown. */
function chooseMove(battle, side, req, rng, opts) {
  const me = side.active[0];
  const opp = oppOf(side).active[0];
  const r = req.active[0];
  const usable = r.moves.map((m, i) => ({...m, slot: i + 1})).filter(m => !m.disabled && (m.pp === undefined || m.pp > 0));
  if (!usable.length) return 'move 1';
  const myIds = usable.map(m => m.id);
  const oppIds = opp.moveSlots.map(m => m.id);
  const my = bestDamage(battle, me, opp, myIds);
  const their = bestDamage(battle, opp, me, oppIds);
  const meFaster = speedOf(battle, me) > speedOf(battle, opp) || (speedOf(battle, me) === speedOf(battle, opp) && rng() < 0.5);
  const iOutspeed = (prio) => prio > their.priority || (prio === their.priority && meFaster);
  const pick = id => `move ${usable.find(m => m.id === id).slot}`;

  // 0) Bloqueado (objeto Elegido / Otra Vez) en un movimiento inútil: cambiar
  if (usable.length === 1 && !r.trapped && !r.maybeTrapped && r.moves.length > 1) {
    const mv = Dex.moves.get(usable[0].id);
    if (mv.category === 'Status' || expectedDamage(battle, me, opp, usable[0].id) < 0.15) {
      const sw = bestSwitch(battle, side, req, opp);
      if (sw) return `switch ${sw.slot}`;
    }
  }
  // 1) Rematar si puedo antes de que me rematen
  if (my.frac >= 1 && (iOutspeed(my.priority) || their.frac < 1)) return pick(my.id);
  // 1b) Prioridad que remata
  for (const id of myIds) {
    const mv = Dex.moves.get(id);
    if (mv.priority > 0 && expectedDamage(battle, me, opp, id) >= 1) return pick(id);
  }

  // 2) Cambiar si me van a debilitar primero y hay alguien que aguante mucho mejor
  if (!r.trapped && !r.maybeTrapped && their.frac >= 1 && !iOutspeed(my.priority)) {
    const sw = bestSwitch(battle, side, req, opp);
    if (sw && sw.score > (opts.P || P).switchKO) return `switch ${sw.slot}`;
  }

  // 2a) Enfrentamiento malo (no hago casi nada y hay un relevo claramente mejor): cambiar
  if (!r.trapped && !r.maybeTrapped && my.frac < (opts.P || P).badMatchupDealt) {
    const cur = (1 - Math.min(1, their.frac)) * 0.7 + Math.min(1, my.frac) * (meFaster ? 0.5 : 0.3);
    const sw = bestSwitch(battle, side, req, opp);
    if (sw && sw.score > cur + (opts.P || P).badMatchup) return `switch ${sw.slot}`;
  }
  const hpFrac = me.hp / me.maxhp;
  // 2b) Si puedo debilitar y no hay cambio mejor, atacar (nunca hacer setup delante de un rival a tiro)
  if (my.frac >= 1) return pick(my.id);
  // 3) Hazards
  for (const m of usable) {
    const h = HAZARDS[m.id];
    if (h && !oppOf(side).sideConditions[h] && their.frac < 0.6 && oppOf(side).pokemonLeft > 2) return pick(m.id);
  }
  // 4) Setup si es seguro
  for (const m of usable) {
    if (!SETUP.has(m.id)) continue;
    const mv = Dex.moves.get(m.id);
    const boosts = mv.boosts || (mv.self && mv.self.boosts) || {};
    const key = Object.keys(boosts)[0];
    if (key && me.boosts[key] >= 4) continue;
    if (m.id === 'bellydrum' && hpFrac < 0.75) continue;
    if (their.frac * (opts.P || P).setupSafety < hpFrac && my.frac < 1) return pick(m.id);
  }
  // 5) Recuperación
  for (const m of usable) {
    if (RECOVERY.has(m.id) && hpFrac < 0.5 && their.frac < 0.45) return pick(m.id);
  }
  // 6) Estados
  let bestStatus = null, bestStatusVal = 0;
  for (const m of usable) {
    const mv = Dex.moves.get(m.id);
    if (mv.category !== 'Status') continue;
    const v = statusMoveValue(battle, me, opp, mv, their.frac);
    if (v > bestStatusVal) { bestStatus = m.id; bestStatusVal = v; }
  }
  if (bestStatus && bestStatusVal > my.frac * 0.9 && their.frac < 0.7) return pick(bestStatus);
  // 7) Limpiar hazards
  const mySide = side.sideConditions;
  if (mySide.stealthrock || mySide.spikes || mySide.toxicspikes || mySide.stickyweb) {
    for (const m of usable) if (REMOVAL.has(m.id) && their.frac < 0.6) return pick(m.id);
  }
  // 8) Mejor daño (con algo de ruido para diversidad); preferir pivotes si el daño es parecido
  if (my.id) {
    let choice = my.id;
    for (const id of myIds) {
      const mv = Dex.moves.get(id);
      if (mv.selfSwitch && my.frac < 1 && expectedDamage(battle, me, opp, id) >= my.frac * 0.8) choice = id;
    }
    if (rng() < (opts.epsilon || 0)) { choice = myIds[Math.floor(rng() * myIds.length)]; TRACE.last = 'epsilon'; } else TRACE.last = 'R8';
    return pick(choice);
  }
  return `move ${usable[Math.floor(rng() * usable.length)].slot}`;
}

/** Mejor relevo contra el activo rival: aguanta su mejor golpe y le hace daño. */
function bestSwitch(battle, side, req, opp) {
  let best = null;
  req.side.pokemon.forEach((pk, i) => {
    if (i === 0 || pk.condition.endsWith(' fnt') || pk.active) return;
    const mon = side.pokemon[i];
    if (!mon || mon.fainted) return;
    const taken = bestDamage(battle, opp, mon, opp.moveSlots.map(m => m.id)).frac;
    const dealt = bestDamage(battle, mon, opp, mon.moveSlots.map(m => m.id)).frac;
    const faster = speedOf(battle, mon) > speedOf(battle, opp);
    let hz = 0;
    const sc = side.sideConditions;
    if (sc.stealthrock && toID(mon.item) !== 'heavydutyboots') hz += 0.125 * Math.pow(2, Dex.getEffectiveness('Rock', mon));
    const score = (1 - Math.min(1, taken + hz)) * 0.7 + Math.min(1, dealt) * (faster ? 0.5 : 0.3);
    if (!best || score > best.score) best = {slot: i + 1, score};
  });
  return best;
}

function chooseForcedSwitch(battle, side, req) {
  const opp = oppOf(side).active[0];
  if (!opp) return 'default';
  const sw = bestSwitch(battle, side, req, opp);
  return sw ? `switch ${sw.slot}` : 'default';
}

function withMega(choice, req) {
  // megaevoluciona en cuanto puede (lo normal en competitivo)
  if (choice && choice.startsWith('move') && req.active && req.active[0] && req.active[0].canMegaEvo) return choice + ' mega';
  return choice;
}

function decide(battle, side, rng, opts) {
  const req = side.activeRequest;
  if (!req || req.wait) return null;
  if (req.teamPreview) return 'default';
  if (req.forceSwitch) return chooseForcedSwitch(battle, side, req);
  if (req.active && opts.epsilon >= 1) { // bot de referencia totalmente aleatorio (para calibrar)
    const ms = req.active[0].moves.map((mv, i) => ({...mv, i})).filter(mv => !mv.disabled);
    return ms.length ? `move ${ms[Math.floor(rng() * ms.length)].i + 1}` : 'default';
  }
  if (req.active) return withMega(chooseMove(battle, side, req, rng, opts), req);
  return 'default';
}

// ---------------------------------------------------------------- partida
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Juega una partida. Devuelve {winner: 'p1'|'p2'|'tie', turns, log?} */
function playBattle(team1, team2, {seed = 1, keepLog = false, maxTurns = 300, epsilon = 0.03, epsilons = null, params = null} = {}) {
  const battle = new Battle({formatid: FORMAT, seed: [seed, seed * 7 + 1, seed * 13 + 2, seed * 31 + 3]});
  battle.setPlayer('p1', {name: 'A', team: team1});
  battle.setPlayer('p2', {name: 'B', team: team2});
  const rng = mulberry32(seed * 9973 + 17);
  let guard = 0;
  while (!battle.ended && battle.turn <= maxTurns && guard++ < 5000) {
    let acted = false;
    for (const side of [battle.p1, battle.p2]) {
      if (side.activeRequest && !side.activeRequest.wait && !side.isChoiceDone()) {
        const eps = epsilons ? epsilons[side.id === 'p1' ? 0 : 1] : epsilon;
        const c = decide(battle, side, rng, {epsilon: eps, P: params ? params[side.id === 'p1' ? 0 : 1] : null});
        if (process.env.SIM_TRACE && side.active[0]) console.error(`T${battle.turn} ${side.id} ${side.active[0].species.name} -> ${c} [${TRACE.last || ''}]`);
        const req = side.activeRequest;
        let ok = false;
        try { ok = battle.choose(side.id, c || 'default'); } catch (e) { ok = false; }
        // OJO: si esta elección completa el turno, el combate avanza y aparece una petición NUEVA.
        // Solo es un rechazo si seguimos ante la MISMA petición sin elección hecha.
        if (!ok && side.activeRequest === req && !side.isChoiceDone()) {
          if (process.env.SIM_TRACE) console.error('ELECCION RECHAZADA', c, side.choice.error);
          side.clearChoice();
          battle.choose(side.id, 'default');
        }
        acted = true;
      }
    }
    if (!acted) break;
  }
  const res = {winner: battle.winner === 'A' ? 'p1' : battle.winner === 'B' ? 'p2' : 'tie', turns: battle.turn};
  if (keepLog) res.log = battle.log.join('\n');
  return res;
}

module.exports = {expectedDamage, decide, BOT_PARAMS: P, applyAnilSpecies, toShowdownSet, randomForeignTeam, playBattle, normNature, FORMAT};
