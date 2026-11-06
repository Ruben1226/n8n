"""Tests del motor. Ejecutar: python -m unittest discover -s tests -v  (desde la raíz del proyecto)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.pkmn.damage import Battler, calc  # noqa: E402
from tools.pkmn.data import Dex  # noqa: E402
from tools.pkmn.stats import calc_stat  # noqa: E402
from tools.pkmn.typechart import effectiveness  # noqa: E402

EJ = os.path.join(os.path.dirname(__file__), "..", "data", "ejemplo")


class TestTipos(unittest.TestCase):
    def test_basicos(self):
        self.assertEqual(effectiveness("Ice", ["Dragon", "Ground"]), 4)
        self.assertEqual(effectiveness("Ground", ["Flying"]), 0)
        self.assertEqual(effectiveness("Fire", ["Water", "Rock"]), 0.25)
        self.assertEqual(effectiveness("Fuego", ["Planta"]), 2)  # nombres en español
        self.assertEqual(effectiveness("Dragon", ["Fairy"]), 0)


class TestStats(unittest.TestCase):
    def test_formula(self):
        self.assertEqual(calc_stat("hp", 108, 100, 31, 0), 357)          # Garchomp nv100 0 EVs
        self.assertEqual(calc_stat("spe", 102, 100, 31, 252, "Jolly"), 333)
        # nivel 49, 0 EVs, Gyarados Firme
        self.assertEqual(calc_stat("atk", 125, 49, 31, 0, "Adamant"), 156)  # floor((floor(281*49/100)+5)*1.1)


class TestDanio(unittest.TestCase):
    def test_ejemplo_bulbapedia(self):
        # Glaceon nv75 Colmillo Hielo vs Garchomp: 168-196 según Bulbapedia
        a = Battler("Glaceon", ["Ice"], {}, level=75,
                    stat_override={"hp": 1, "atk": 123, "def": 1, "spa": 1, "spd": 1, "spe": 1})
        d = Battler("Garchomp", ["Dragon", "Ground"], {},
                    stat_override={"hp": 300, "atk": 1, "def": 163, "spa": 1, "spd": 1, "spe": 1})
        r = calc(a, d, {"name": "Ice Fang", "type": "Ice", "category": "physical", "power": 65})
        self.assertEqual((r["min"], r["max"]), (168, 196))

    def test_habilidades(self):
        dex = Dex(EJ)
        base = {"hp": 80, "atk": 100, "def": 80, "spa": 80, "spd": 80, "spe": 80}
        tackle = dex.move("Body Slam")
        normal = Battler("X", ["Normal"], base, ability="Aerilate", ability_effects=dex.ability_effects("Aerilate"))
        grass = Battler("Y", ["Grass"], base)
        r = calc(normal, grass, tackle)
        self.assertEqual(r["type"], "Flying")
        self.assertEqual(r["eff"], 2)
        lev = Battler("Z", ["Normal"], base, ability="Levitate", ability_effects=dex.ability_effects("Levitate"))
        self.assertEqual(calc(normal, lev, dex.move("Earthquake"))["max"], 0)
        huge = Battler("H", ["Water"], base, ability_effects=dex.ability_effects("Huge Power"))
        plain = Battler("P", ["Water"], base)
        eq = dex.move("Earthquake")
        self.assertGreater(calc(huge, grass if False else plain, eq)["max"], 1.8 * calc(plain, plain, eq)["max"])

    def test_dano_fijo_nivel(self):
        dex = Dex(EJ)
        base = {"hp": 80, "atk": 100, "def": 80, "spa": 80, "spd": 80, "spe": 80}
        a = Battler("A", ["Fairy"], base, level=49)
        d = Battler("D", ["Normal"], base)
        self.assertEqual(calc(a, d, dex.move("Seismic Toss"))["max"], 49)


class TestDatos(unittest.TestCase):
    def test_prohibidos(self):
        dex = Dex(EJ)
        self.assertNotIn("Last Respects", dex.legal_moves(dex.species("Gengar")))
        self.assertEqual(dex.validate(), [])


if __name__ == "__main__":
    unittest.main()
