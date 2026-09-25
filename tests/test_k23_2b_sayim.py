"""k23-2b sayim kurallarinin testi (GPU'suz). Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "deneyler"))

import k23_2b_sayim as sayim  # noqa: E402


class TestK232bSayim(unittest.TestCase):
    def test_turkce_cevap(self):
        self.assertTrue(sayim.turkce_mi("Bugün hava çok güzel, dışarı çıkalım mı?"))

    def test_ingilizce_cevap(self):
        self.assertFalse(sayim.turkce_mi("What is the answer to this question and you know it"))

    def test_kalip_emoji_markdown(self):
        s = sayim.say("Elbette! Size nasıl yardımcı olabilirim? 😊\n**Not:** şu\n- madde")
        self.assertEqual((s["asistan"], s["emoji"], s["markdown"]), (3, 1, 2))

    def test_temiz_cevap(self):
        self.assertEqual(sayim.say("Valla bilmiyorum, bakarım."),
                         {"turkce": True, "asistan": 0, "emoji": 0, "markdown": 0})


if __name__ == "__main__":
    unittest.main()
