"""Gomme portunun Kafa ve web sohbet portlariyla cakismadigini denetler (port-a).
Cagiran: `python -m unittest discover -s tests`."""

import unittest

from agiz import web_sohbet
from ortak import ayar


class GommePortTest(unittest.TestCase):
    def test_portlar_ayri(self):
        self.assertNotIn(ayar.GOMME_PORT, (ayar.KAFA_PORT, web_sohbet.PORT))

    def test_uc_portu_kullanir(self):
        self.assertIn(f":{ayar.GOMME_PORT}/", ayar.GOMME_UC)


if __name__ == "__main__":
    unittest.main()
