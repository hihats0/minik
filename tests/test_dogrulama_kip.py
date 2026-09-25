"""dogrulama_kaybi modeli onceki kipine birakir (K41-B: hep train()'e donuyordu, agac yumusak olculdu).
Cagiran: `python -m pytest tests/test_dogrulama_kip.py`."""

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cocuk import egit_araclari as ea

SOZLUK, BAGLAM = 32, 8


class Minik(nn.Module):
    def __init__(self):
        super().__init__()
        self.gomme = nn.Embedding(SOZLUK, SOZLUK)

    def forward(self, ids):
        return self.gomme(ids)


def kos(model):
    veri = np.arange(200, dtype=np.uint16) % SOZLUK
    ea.dogrulama_kaybi(model, veri, BAGLAM, 2, 4, torch.device("cpu"), False)


def test_eval_kipi_korunur():
    model = Minik().eval()
    kos(model)
    assert not model.training


def test_egitim_kipi_korunur():
    model = Minik().train()
    kos(model)
    assert model.training
