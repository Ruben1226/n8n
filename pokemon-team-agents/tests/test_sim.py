"""Test de integración del simulador (se salta si no están instaladas las dependencias de Node)."""
import json
import os
import shutil
import subprocess
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HAS_NODE = shutil.which("node") and os.path.isdir(os.path.join(ROOT, "sim", "node_modules", "pokemon-showdown"))


@unittest.skipUnless(HAS_NODE, "Node o sim/node_modules no disponibles (cd sim && npm install)")
class TestSimulador(unittest.TestCase):
    def test_partida_y_parches(self):
        js = r"""
        const m = require('./sim/motor-sim');
        const {Dex} = require('./sim/node_modules/pokemon-showdown');
        m.applyAnilSpecies([{name: 'Pikachu', types: ['Agua'], base_stats: {hp: 10, atk: 20, def: 30, spa: 40, spd: 50, spe: 60}}]);
        const sp = Dex.species.get('pikachu');
        const r = m.playBattle(m.randomForeignTeam(49, 1), m.randomForeignTeam(49, 2), {seed: 3});
        const r2 = m.playBattle(m.randomForeignTeam(49, 1), m.randomForeignTeam(49, 2), {seed: 3});
        console.log(JSON.stringify({types: sp.types, spe: sp.baseStats.spe, w: r.winner, w2: r2.winner, t: r.turns, t2: r2.turns, fmt: m.FORMAT}));
        """
        out = json.loads(subprocess.check_output(["node", "-e", js], cwd=ROOT).decode().strip().splitlines()[-1])
        self.assertEqual(out["types"], ["Water"])
        self.assertEqual(out["spe"], 60)
        self.assertIn(out["w"], ("p1", "p2", "tie"))
        self.assertEqual((out["w"], out["t"]), (out["w2"], out["t2"]))  # reproducible con la misma semilla
        self.assertIn("Sleep Clause Mod", out["fmt"])

    def test_sin_elecciones_forzadas(self):
        """Regresión: al completar un turno no debe forzarse 'default' en el turno siguiente."""
        js = r"""
        const m = require('./sim/motor-sim');
        for (let i = 0; i < 5; i++) m.playBattle(m.randomForeignTeam(49, 10 + i), m.randomForeignTeam(49, 20 + i), {seed: i + 1});
        """
        import os as _os
        env = dict(_os.environ, SIM_TRACE="1")
        err = subprocess.run(["node", "-e", js], cwd=ROOT, env=env, capture_output=True, text=True).stderr
        self.assertNotIn("ELECCION RECHAZADA", err)


if __name__ == "__main__":
    unittest.main()
