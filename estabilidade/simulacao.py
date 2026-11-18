"""Resposta ao degrau em malha fechada (realimentação unitária), com atraso exato.

L(s) = N(s)/D(s) e^{-τs} é realizado na forma canônica controlável; o atraso é
um buffer circular sobre o sinal de erro. Integração por Runge–Kutta 4 com passo fixo.
"""
from __future__ import annotations

import numpy as np

from . import polinomios as P
from .sistema import FuncaoTransferencia


def _espaco_estados(num, den):
    den = P.normalizar(den); num = P.normalizar(num)
    a0 = den[0]
    den = den / a0; num = num / a0
    n = len(den) - 1
    num = np.concatenate([np.zeros(n + 1 - len(num)), num])
    d = num[0]
    b = num[1:] - d * den[1:]               # remove parte direta
    A = np.zeros((n, n))
    A[0, :] = -den[1:]
    if n > 1:
        A[1:, :-1] = np.eye(n - 1)
    B = np.zeros(n); B[0] = 1.0
    C = b.copy()
    return A, B, C, d


def degrau_malha_fechada(L: FuncaoTransferencia, t_final=20.0, dt=1e-3, limite=1e6):
    A, B, C, D = _espaco_estados(L.num, L.den)
    n_atraso = int(round(L.atraso / dt))
    buf = np.zeros(max(n_atraso, 1))
    x = np.zeros(A.shape[0])
    passos = int(t_final / dt)
    t = np.arange(passos) * dt
    y = np.zeros(passos)
    f = lambda x, u: A @ x + B * u
    for k in range(passos):
        # O atraso fica na entrada da planta: u(t) = e(t - τ), e = r - y, r = 1.
        if n_atraso:
            u = buf[k % n_atraso]            # e(t - τ)
            yk = C @ x + D * u
            buf[k % n_atraso] = 1.0 - yk     # guarda e(t)
        else:
            yk = (C @ x + D) / (1.0 + D)     # resolve o laço algébrico se D != 0
            u = 1.0 - yk
        y[k] = yk
        k1 = f(x, u); k2 = f(x + dt / 2 * k1, u); k3 = f(x + dt / 2 * k2, u); k4 = f(x + dt * k3, u)
        x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if not np.isfinite(yk) or abs(yk) > limite:
            y[k:] = np.nan
            break
    return t, y
