"""Os quatro sistemas de benchmark exigidos pelo projeto (Fase 1)."""
from __future__ import annotations

from . import polinomios as P
from .sistema import FuncaoTransferencia


def sistema_A(K=50.0):
    """A – Padrão: 3ª ordem estável em MA.  L(s) = K / ((s+1)(s+2)(s+5)).
    Routh: estável para 0 < K < 126."""
    den = P.de_raizes([-1, -2, -5])
    return FuncaoTransferencia([K], den, 0.0, "A", "3ª ordem estável em MA")


def sistema_B(K=100.0):
    """B – Instável em MA: pêndulo invertido linearizado 1/(s²-4) com compensador
    de avanço (s+1)/(s+10).  L(s) = K (s+1) / ((s-2)(s+2)(s+10)).  P = 1.
    Routh: estável para K > 40."""
    den = P.de_raizes([2, -2, -10])
    return FuncaoTransferencia(P.escalar([1, 1], K), den, 0.0, "B", "Pêndulo invertido + avanço (P=1)")


def sistema_C(K=2.0):
    """C – Fase não-mínima: zero no SPD e integrador.  L(s) = K (1-s) / (s (s+2)(s+3)).
    Routh: estável para 0 < K < 5. O polo em s=0 exige indentação no contorno."""
    den = P.de_raizes([0, -2, -3])
    return FuncaoTransferencia(P.escalar([-1, 1], K), den, 0.0, "C", "Zero no SPD + integrador")


def sistema_D(K=2.0, tau=0.5):
    """D – Atraso de transporte: L(s) = K e^{-τs} / ((s+1)(0.5s+1)), τ = 0,5 s
    (ex.: malha fechada através de uma rede com latência)."""
    den = P.multiplicar([1, 1], [0.5, 1])
    return FuncaoTransferencia([K], den, tau, "D", "2ª ordem com atraso de rede")


TODOS = {"A": sistema_A, "B": sistema_B, "C": sistema_C, "D": sistema_D}
