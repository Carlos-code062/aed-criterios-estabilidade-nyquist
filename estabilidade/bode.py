"""Diagrama de Bode: resposta em frequência exata e aproximação assintótica."""
from __future__ import annotations

import numpy as np

from .nyquist import fase_continua
from .sistema import FuncaoTransferencia


def bode(L: FuncaoTransferencia, w=None, n=2000):
    """Retorna (ω, |L| em dB, fase em graus) com fase contínua (sem unwrap)."""
    if w is None:
        r = np.concatenate([L.polos(), L.zeros()])
        mags = np.abs(r[np.abs(r) > 1e-9])
        lo = min([1.0] + list(mags)); hi = max([1.0] + list(mags))
        w = np.logspace(np.log10(lo) - 2, np.log10(hi) + 2, n)
    mag_db = 20 * np.log10(np.abs(L.resposta_frequencia(w)))
    fase = np.degrees(fase_continua(L, w))
    # convenção de apresentação: fase em baixa frequência no intervalo (-360°, 0°]
    fase -= 360.0 * np.ceil((fase[0] - 1e-9) / 360.0)
    return w, mag_db, fase


def bode_assintotico(L: FuncaoTransferencia, w):
    """Aproximação por retas: cada raiz real/complexa contribui ±20 dB/déc
    a partir da sua frequência de canto |r|; raízes em s=0 contribuem desde ω→0."""
    w = np.asarray(w, dtype=float)
    # ganho de "baixa frequência" na forma de Bode
    def parcela(raizes, sinal):
        out = np.zeros_like(w)
        k = 1.0
        for r in raizes:
            a = abs(r)
            if a < 1e-9:
                out += sinal * 20 * np.log10(w)
            else:
                out += sinal * np.where(w > a, 20 * np.log10(w / a), 0.0)
                k *= a ** sinal
        return out, k
    z, kz = parcela(L.zeros(), +1)
    p, kp = parcela(L.polos(), -1)
    k0 = abs(L.num[0] / L.den[0]) * kz * kp
    return 20 * np.log10(k0) + z + p
