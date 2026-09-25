"""f3d_ortak testleri: p95 ve sicaklik histerezisi.
Cagiran: python -m unittest discover -s tests.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "deneyler"))
from f3d_ortak import p95, sicaklik_durumu  # noqa: E402


class F3dOrtakTest(unittest.TestCase):
    def test_p95(self):
        self.assertEqual(p95(list(range(1, 101))), 95)
        self.assertEqual(p95([5]), 5)

    def test_histerezis(self):
        self.assertTrue(sicaklik_durumu(90, False))
        self.assertTrue(sicaklik_durumu(75, True))
        self.assertFalse(sicaklik_durumu(75, False))
        self.assertFalse(sicaklik_durumu(70, True))


if __name__ == "__main__":
    unittest.main()
