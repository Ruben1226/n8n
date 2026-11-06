#!/usr/bin/env node
'use strict';
/**
 * Validación empírica por simulación (motor oficial de Showdown + bot heurístico).
 *
 * Uso:
 *   node sim/simular.js --equipos workspace/07_sim/equipos.json --rivales workspace/07_sim/rivales.json \
 *        [--random-rivales 30] [--n 4] [--datos workspace/01_datos] [--logs workspace/07_sim/logs] \
 *        [--out workspace/07_sim/resultados.json]
 *
 * equipos.json / rivales.json: [{"nombre": "...", "sets": [ <set del motor Python>, ... x6 ]}, ...]
 * --random-rivales K: añade K equipos de "otro jugador random" (generador oficial de Random Battle, nv49, 0 EVs).
 * --n: partidas por emparejamiento (se alterna el lado p1/p2).
 */
const fs = require('fs');
const path = require('path');
const m = require('./motor-sim');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > -1 ? process.argv[i + 1] : def;
}
const ROOT = path.resolve(__dirname, '..');
const rel = p => path.isAbsolute(p) ? p : path.join(ROOT, p);
const datos = rel(arg('datos', 'workspace/01_datos'));
const equiposF = rel(arg('equipos', 'workspace/07_sim/equipos.json'));
const rivalesF = arg('rivales', null);
const K = parseInt(arg('random-rivales', '30'), 10);
const N = parseInt(arg('n', '4'), 10);
const logsDir = arg('logs', null) ? rel(arg('logs')) : null;
const outF = rel(arg('out', 'workspace/07_sim/resultados.json'));
const seed0 = parseInt(arg('semilla', '1'), 10);

const warnings = [];
const pk = path.join(datos, 'pokemon.json');
let reglas = {};
try { reglas = JSON.parse(fs.readFileSync(path.join(ROOT, 'config', 'reglas.json'), 'utf8')); } catch (e) {}
// Solo se parchean especies si los combates se juegan con los datos de Añil. En Showdown Custom Game
// (lo habitual) mandan los tipos y stats OFICIALES de Showdown.
if (reglas.datos_especie === 'anil' && fs.existsSync(pk)) warnings.push(...m.applyAnilSpecies(JSON.parse(fs.readFileSync(pk, 'utf8'))));

function loadTeams(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8')).map((t, i) => {
    const sets = (t.sets || t).map(s => {
      const sd = m.toShowdownSet(s, 49, warnings);
      if (sd.moves.length < (s.moves || []).length) warnings.push(`${t.nombre || i}: ${s.species} tiene movimientos desconocidos para Showdown: ${(s.moves || []).join(', ')} (usa showdown_moves)`);
      return sd;
    });
    return {nombre: t.nombre || `equipo_${i}`, sets};
  });
}

const equipos = loadTeams(equiposF);
let rivales = rivalesF ? loadTeams(rel(rivalesF)) : [];
for (let i = 0; i < K; i++) rivales.push({nombre: `random_${i}`, sets: m.randomForeignTeam(49, seed0 * 100003 + i), random: true});

function wilson(w, n) {
  if (!n) return [0, 0];
  const z = 1.96, p = w / n, d = 1 + z * z / n;
  const c = (p + z * z / (2 * n)) / d, h = (z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}

function memberStats(log, side) {
  // cuenta debilitados propios y KOs causados por cada miembro (aprox: último atacante del rival)
  const faints = {}, kos = {};
  let lastMove = {p1: null, p2: null};
  for (const line of log.split('\n')) {
    const parts = line.split('|');
    if (parts[1] === 'move') {
      const who = parts[2].slice(0, 2), name = parts[2].split(': ')[1];
      lastMove[who] = name;
    } else if (parts[1] === 'faint') {
      const who = parts[2].slice(0, 2), name = parts[2].split(': ')[1];
      const foe = who === 'p1' ? 'p2' : 'p1';
      if (who === side) faints[name] = (faints[name] || 0) + 1;
      else if (lastMove[side]) kos[lastMove[side]] = (kos[lastMove[side]] || 0) + 1;
    }
  }
  return {faints, kos};
}

const resultados = [];
const t0 = Date.now();
for (const eq of equipos) {
  const res = {nombre: eq.nombre, partidas: 0, victorias: 0, vs: {}, miembros: {}, turnos: 0, derrotas_log: []};
  for (const [ri, r] of rivales.entries()) {
    if (r.nombre === eq.nombre) continue;
    let w = 0;
    for (let g = 0; g < N; g++) {
      const swap = g % 2 === 1;
      // mismas semillas para todos los equipos (números aleatorios comunes): reduce la varianza al comparar
      const seed = seed0 * 7919 + ri * 101 + g + 1;
      const out = m.playBattle(swap ? r.sets : eq.sets, swap ? eq.sets : r.sets, {seed, keepLog: true});
      const mySide = swap ? 'p2' : 'p1';
      const won = out.winner === mySide;
      w += won ? 1 : out.winner === 'tie' ? 0.5 : 0;
      res.turnos += out.turns;
      const st = memberStats(out.log, mySide);
      for (const s of eq.sets) {
        const k = s.name;
        res.miembros[k] = res.miembros[k] || {debilitado: 0, kos: 0};
        res.miembros[k].debilitado += st.faints[k] || 0;
        res.miembros[k].kos += st.kos[k] || 0;
      }
      if (!won && logsDir && res.derrotas_log.length < 6) {
        fs.mkdirSync(logsDir, {recursive: true});
        const f = path.join(logsDir, `${eq.nombre}__vs__${r.nombre}__${seed}.log`.replace(/[^\w.\-]/g, '_'));
        fs.writeFileSync(f, out.log);
        res.derrotas_log.push(path.relative(ROOT, f));
      }
    }
    res.vs[r.nombre] = {winrate: +(w / N).toFixed(3), random: !!r.random};
    res.victorias += w; res.partidas += N;
  }
  res.winrate = +(res.victorias / res.partidas).toFixed(4);
  res.ic95 = wilson(res.victorias, res.partidas).map(x => +x.toFixed(3));
  const randomVs = Object.values(res.vs).filter(v => v.random);
  const poolVs = Object.values(res.vs).filter(v => !v.random);
  res.winrate_vs_random = randomVs.length ? +(randomVs.reduce((s, v) => s + v.winrate, 0) / randomVs.length).toFixed(3) : null;
  res.winrate_vs_pool = poolVs.length ? +(poolVs.reduce((s, v) => s + v.winrate, 0) / poolVs.length).toFixed(3) : null;
  res.peores_rivales = Object.entries(res.vs).sort((a, b) => a[1].winrate - b[1].winrate).slice(0, 5).map(([k, v]) => ({rival: k, winrate: v.winrate}));
  res.turnos = +(res.turnos / res.partidas).toFixed(1);
  resultados.push(res);
  process.stderr.write(`${eq.nombre}: winrate ${res.winrate} IC95 ${res.ic95} (${res.partidas} partidas)\n`);
}
resultados.sort((a, b) => b.winrate - a.winrate);
fs.mkdirSync(path.dirname(outF), {recursive: true});
fs.writeFileSync(outF, JSON.stringify({formato: m.FORMAT, partidas_por_emparejamiento: N, rivales: rivales.map(r => r.nombre),
  segundos: (Date.now() - t0) / 1000, avisos: [...new Set(warnings)], resultados}, null, 1));
console.log(`-> ${path.relative(ROOT, outF)}  (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
for (const r of resultados) console.log(`${r.winrate.toFixed(3)}  [${r.ic95.join('-')}]  ${r.nombre}`);
if (warnings.length) console.log('AVISOS:\n' + [...new Set(warnings)].join('\n'));
