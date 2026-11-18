"""Aproximação racional de Padé para o atraso e^{-τs}.

e^{-τs} ≈ Q(-τs)/Q(τs),   Q(x) = Σ_{k=0}^{n} c_k x^k,
c_k = (2n-k)! n! / ((2n)! k! (n-k)!).
"""
from __future__ import annotations

from math import factorial

import numpy as np

from . import polinomios as P
from .sistema import FuncaoTransferencia


def pade(tau: float, ordem: int):
    n = ordem
    c = [factorial(2 * n - k) * factorial(n) / (factorial(2 * n) * factorial(k) * factorial(n - k))
         for k in range(n + 1)]
    # coeficientes em potências crescentes de s; converte para decrescentes
    den = np.array([c[k] * tau ** k for k in range(n + 1)])[::-1]
    num = np.array([c[k] * (-tau) ** k for k in range(n + 1)])[::-1]
    return P.normalizar(num), P.normalizar(den)


def substituir_atraso(L: FuncaoTransferencia, ordem: int) -> FuncaoTransferencia:
    """Retorna L(s) racional com e^{-τs} trocado por Padé de ordem `ordem`."""
    if not L.atraso:
        return L
    pn, pd = pade(L.atraso, ordem)
    return FuncaoTransferencia(P.multiplicar(L.num, pn), P.multiplicar(L.den, pd), 0.0,
                               L.nome + f" (Padé {ordem})", L.descricao)
