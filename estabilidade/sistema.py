"""Representação de funções de transferência L(s) = K * N(s)/D(s) * e^{-tau s}."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import polinomios as P


@dataclass
class FuncaoTransferencia:
    num: np.ndarray
    den: np.ndarray
    atraso: float = 0.0          # tau [s], termo e^{-tau s}
    nome: str = ""
    descricao: str = ""

    def __post_init__(self):
        self.num = P.normalizar(np.asarray(self.num, dtype=float))
        self.den = P.normalizar(np.asarray(self.den, dtype=float))
        if P.grau(self.num) > P.grau(self.den):
            raise ValueError("Função de transferência imprópria (grau num > grau den).")

    # ---------------------------------------------------------------- avaliação
    def __call__(self, s):
        s = np.asarray(s, dtype=complex)
        g = P.horner(self.num, s) / P.horner(self.den, s)
        if self.atraso:
            g = g * np.exp(-self.atraso * s)
        return g

    def resposta_frequencia(self, w):
        return self(1j * np.asarray(w, dtype=float))

    # ------------------------------------------------------------ propriedades
    def polos(self):
        return P.raizes(self.den)

    def zeros(self):
        return P.raizes(self.num)

    def polos_instaveis_ma(self, tol=1e-9) -> int:
        """P: número de polos de malha aberta no semiplano direito (Re > 0)."""
        return int(np.sum(self.polos().real > tol))

    def estritamente_propria(self) -> bool:
        return P.grau(self.num) < P.grau(self.den)

    def com_ganho(self, k: float) -> "FuncaoTransferencia":
        return FuncaoTransferencia(P.escalar(self.num, k), self.den.copy(), self.atraso,
                                   self.nome, self.descricao)

    def com_atraso(self, tau: float) -> "FuncaoTransferencia":
        return FuncaoTransferencia(self.num.copy(), self.den.copy(), tau, self.nome, self.descricao)

    def polinomio_caracteristico(self) -> np.ndarray:
        """1 + L(s) = 0  ->  D(s) + N(s) = 0 (somente sem atraso)."""
        if self.atraso:
            raise ValueError("Com atraso a equação característica é transcendental; use Padé.")
        return P.somar(self.den, self.num)

    def polos_malha_fechada(self):
        return P.raizes(self.polinomio_caracteristico())

    def __repr__(self):
        a = f" e^(-{self.atraso}s)" if self.atraso else ""
        return f"L(s) = {np.round(self.num, 4).tolist()}/{np.round(self.den, 4).tolist()}{a}"
