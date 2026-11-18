"""Critério de Routh–Hurwitz, implementado do zero.

Inclui os dois casos especiais clássicos:
* Zero na primeira coluna (linha não nula): substitui-se o zero por ε > 0 pequeno.
* Linha inteira nula: indica raízes simétricas em relação à origem; a linha é
  substituída pelos coeficientes da derivada do polinômio auxiliar formado pela
  linha anterior.

Suporta aritmética de ponto flutuante (float) ou exata (fractions.Fraction),
o que permite medir o erro de arredondamento da tabela ao crescer a ordem.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from . import polinomios as P


@dataclass
class ResultadoRouth:
    tabela: list                   # lista de linhas (listas)
    primeira_coluna: list
    trocas_sinal: int              # = nº de raízes no semiplano direito
    estavel: bool
    linha_nula: bool = False       # ocorreu linha inteira nula (raízes simétricas)
    zero_primeira_coluna: bool = False
    polinomio_auxiliar: list = field(default_factory=list)
    marginal: bool = False         # possíveis raízes sobre o eixo jω

    def resumo(self):
        txt = f"trocas de sinal = {self.trocas_sinal} -> "
        if self.marginal and self.trocas_sinal == 0:
            txt += "MARGINALMENTE ESTÁVEL (raízes sobre jω)"
        else:
            txt += "ESTÁVEL" if self.estavel else "INSTÁVEL"
        if self.zero_primeira_coluna:
            txt += " [caso especial: zero na 1ª coluna, método ε]"
        if self.linha_nula:
            txt += " [caso especial: linha nula, polinômio auxiliar]"
        return txt


def tabela_routh(coef, exato: bool = False, eps=None, tol: float | None = None) -> ResultadoRouth:
    """Monta a tabela de Routh.

    exato=True usa frações (aritmética racional sem arredondamento); nesse caso
    um elemento só é considerado nulo se for exatamente zero (tol = 0).
    """
    p = P.normalizar(np.asarray(coef, dtype=float))
    if p[0] < 0:
        p = -p
    n = len(p) - 1
    if exato:
        conv = lambda x: x if isinstance(x, Fraction) else Fraction(float(x))  # conversão EXATA do float
        zero = Fraction(0)
        eps = Fraction(1, 10**9) if eps is None else Fraction(eps)
        tol = 0 if tol is None else tol
    else:
        conv = float
        zero = 0.0
        eps = 1e-9 if eps is None else eps
        tol = 1e-12 if tol is None else tol

    largura = n // 2 + 1
    l0 = [conv(c) for c in p[0::2]] + [zero] * largura
    l1 = [conv(c) for c in p[1::2]] + [zero] * largura
    tab = [l0[:largura], l1[:largura]]
    # escala de cada elemento = magnitude dos termos que o formaram; um elemento é
    # tratado como "zero" quando é desprezível frente à SUA escala (cancelamento
    # catastrófico), e não frente ao maior coeficiente do polinômio.
    escalas = [[abs(x) for x in tab[0]], [abs(x) for x in tab[1]]]
    res = ResultadoRouth([], [], 0, False)

    for i in range(2, n + 1):
        a, b = tab[i - 2], tab[i - 1]
        ea, eb = escalas[i - 2], escalas[i - 1]
        # caso especial 2: linha inteira nula
        if all(abs(x) <= tol * e for x, e in zip(b, eb)):
            res.linha_nula = True
            res.marginal = True
            ordem = n - i + 2                 # grau do polinômio auxiliar (linha a)
            # linha a representa a_0 s^ordem + a_1 s^(ordem-2) + ...
            aux = a
            res.polinomio_auxiliar = [float(x) for x in aux]
            b = ([aux[k] * (ordem - 2 * k) for k in range(len(aux))] + [zero] * largura)[:largura]
            eb = [abs(x) for x in b]
            tab[i - 1], escalas[i - 1] = b, eb
        # caso especial 1: zero na primeira coluna
        if abs(b[0]) <= tol * eb[0]:
            res.zero_primeira_coluna = True
            b = list(b)
            b[0] = eps * (max(abs(x) for x in a) or 1)
            tab[i - 1] = b
        nova, enova = [], []
        for j in range(largura):
            a_j1 = a[j + 1] if j + 1 < largura else zero
            b_j1 = b[j + 1] if j + 1 < largura else zero
            nova.append((b[0] * a_j1 - a[0] * b_j1) / b[0])
            enova.append((abs(b[0] * a_j1) + abs(a[0] * b_j1)) / abs(b[0]))
        tab.append(nova)
        escalas.append(enova)
    tab = tab[:n + 1]
    col = [linha[0] for linha in tab]
    # se a última linha ficou nula (ex.: raiz em s=0), trata como marginal
    if p[-1] == 0:
        res.marginal = True
        col = col[:-1]
    sinais = [1 if x > 0 else -1 for x in col if x != 0]
    trocas = sum(1 for k in range(1, len(sinais)) if sinais[k] != sinais[k - 1])
    res.tabela = tab
    res.primeira_coluna = col
    res.trocas_sinal = trocas
    res.estavel = trocas == 0 and not res.marginal
    return res


def estavel_routh(coef) -> bool:
    return tabela_routh(coef).estavel


def faixa_ganho(num, den, k_max=1e4, n=4000):
    """Intervalos de K>0 em que D(s) + K N(s) é Hurwitz (varredura + bisseção via Routh)."""
    ks = np.concatenate([[0.0], np.logspace(-4, np.log10(k_max), n)])
    est = np.array([estavel_routh(P.somar(den, P.escalar(num, k))) if k > 0 else False for k in ks])
    est[0] = est[1] if len(est) > 1 else False
    fronteiras = []
    for i in np.flatnonzero(est[1:] != est[:-1]):
        a, b = ks[i], ks[i + 1]
        ea = est[i]
        for _ in range(80):
            m = 0.5 * (a + b)
            if estavel_routh(P.somar(den, P.escalar(num, m))) == ea:
                a = m
            else:
                b = m
        fronteiras.append(0.5 * (a + b))
    intervalos = []
    inicio = 0.0 if est[0] else None
    for f in fronteiras:
        if inicio is None:
            inicio = f
        else:
            intervalos.append((inicio, f))
            inicio = None
    if inicio is not None:
        intervalos.append((inicio, np.inf))
    return intervalos
