"""Lugar das Raízes (Root Locus), implementado do zero.

Para L(s) = K N(s)/D(s), os polos de malha fechada são as raízes de
D(s) + K N(s) = 0. O traçado é feito por:
* passo ADAPTATIVO em K: o passo é reduzido sempre que algum ramo se move mais
  que `dmax` (relativo à escala do sistema) entre dois valores de K;
* ORDENAÇÃO DOS RAMOS por correspondência ao vizinho mais próximo (algoritmo
  guloso sobre a matriz de distâncias), garantindo continuidade das curvas;
* regras geométricas clássicas: centroide e ângulos das assíntotas, pontos de
  separação/chegada (raízes de N'D - ND' = 0) e cruzamentos do eixo jω.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import polinomios as P
from .sistema import FuncaoTransferencia


def _ordenar(anteriores: np.ndarray, novas: np.ndarray) -> np.ndarray:
    n = len(anteriores)
    dist = np.abs(anteriores[:, None] - novas[None, :])
    saida = np.empty(n, dtype=complex)
    livres_a, livres_n = set(range(n)), set(range(n))
    for _ in range(n):
        sub = [(dist[i, j], i, j) for i in livres_a for j in livres_n]
        _, i, j = min(sub)
        saida[i] = novas[j]
        livres_a.remove(i); livres_n.remove(j)
    return saida


@dataclass
class LugarRaizes:
    ganhos: np.ndarray        # (m,)
    ramos: np.ndarray         # (m, n) raízes ordenadas por ramo
    centroide: float
    angulos_assintotas: np.ndarray   # graus
    pontos_separacao: np.ndarray     # pontos reais com K>0
    cruzamentos_jw: list             # [(K, ω)]
    n_raizes_calculadas: int


def lugar_das_raizes(L: FuncaoTransferencia, k_max=None, dmax=0.02, max_pts=4000) -> LugarRaizes:
    N, D = L.num, L.den
    n, m = P.grau(D), P.grau(N)
    escala = max(1.0, np.max(np.abs(np.concatenate([L.polos(), L.zeros()]))))
    if k_max is None:
        # suficientemente grande para os ramos se aproximarem dos zeros/assíntotas
        k_max = 1e3 * abs(D[0] / N[0]) * escala ** (n - m) if n > m else 1e3
    ks = [0.0]
    r = P.raizes(D)
    if len(r) < n:
        r = np.concatenate([r, np.full(n - len(r), np.inf)])
    ramos = [r]
    k, dk = 0.0, k_max * 1e-6
    calc = 1
    while k < k_max and len(ks) < max_pts:
        kn = min(k + dk, k_max)
        rn = P.raizes(P.somar(D, P.escalar(N, kn)))
        calc += 1
        rn = _ordenar(ramos[-1], rn)
        mov = np.max(np.abs(rn - ramos[-1]))
        if mov > dmax * escala and dk > 1e-12 * k_max:
            dk *= 0.5
            continue
        ks.append(kn); ramos.append(rn); k = kn
        if mov < 0.25 * dmax * escala:
            dk *= 2.0
    # ---- regras geométricas
    q = n - m
    if q > 0:
        centroide = (np.sum(L.polos().real) - np.sum(L.zeros().real)) / q
        angs = np.array([(2 * i + 1) * 180.0 / q for i in range(q)])
    else:
        centroide, angs = np.nan, np.array([])
    # pontos de separação: dK/ds = 0  <=>  N'D - N D' = 0, com K = -D/N real e > 0
    cand = P.raizes(P.somar(P.multiplicar(P.derivar(N), D), P.escalar(P.multiplicar(N, P.derivar(D)), -1)))
    sep = []
    for c in cand:
        if abs(c.imag) < 1e-6:
            kc = -P.horner(D, c.real) / P.horner(N, c.real)
            if abs(kc.imag) < 1e-6 and kc.real > 0:
                sep.append(c.real)
    # cruzamentos do eixo jω: D(jω) + K N(jω) = 0 -> K = -D(jω)/N(jω) real positivo
    w = np.logspace(-4, np.log10(100 * escala), 20000)
    kw = -P.horner(D, 1j * w) / P.horner(N, 1j * w)
    cruz = []
    im = kw.imag
    for i in np.flatnonzero(np.sign(im[1:]) != np.sign(im[:-1])):
        a, b = w[i], w[i + 1]
        fa = im[i]
        for _ in range(100):
            c = 0.5 * (a + b)
            fc = (-P.horner(D, 1j * c) / P.horner(N, 1j * c)).imag
            if np.sign(fc) == np.sign(fa):
                a, fa = c, fc
            else:
                b = c
        wc = 0.5 * (a + b)
        kc = (-P.horner(D, 1j * wc) / P.horner(N, 1j * wc)).real
        if kc > 0:
            cruz.append((float(kc), float(wc)))
    # cruzamento em s = 0 (K = -D(0)/N(0))
    if abs(P.horner(N, 0)) > 0:
        k0 = (-P.horner(D, 0) / P.horner(N, 0)).real
        if k0 > 0:
            cruz.append((float(k0), 0.0))
    return LugarRaizes(np.array(ks), np.array(ramos), centroide, angs,
                       np.array(sorted(sep)), sorted(cruz), calc)
