"""Critério de estabilidade de Nyquist, implementado do zero.

Etapas:
1. Constrói o contorno de Nyquist Γ no plano s (eixo jω de -jR a +jR, com
   pequenas indentações semicirculares à direita de polos sobre o eixo jω,
   fechado por um semicírculo de raio R no semiplano direito, sentido horário).
2. Mapeia Γ por F(s) = 1 + L(s) com AMOSTRAGEM ADAPTATIVA: um trecho é
   subdividido enquanto a variação de arg F entre pontos vizinhos exceder
   `passo_max` rad. Isso garante que o ângulo acumulado seja exato (não há
   ambiguidade de 2π entre amostras), inclusive com atraso e^{-τs}, cuja fase
   gira sem limite – mas só onde |L| é relevante.
3. Número de voltas (winding number) de F em torno da origem = voltas de L em
   torno de -1: w = Σ arg(F_{k+1}/F_k) / 2π  (positivo = anti-horário).
4. N (voltas horárias) = -w ;  Z = N + P.

Também calcula margens de ganho, fase e atraso a partir da resposta em frequência.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .sistema import FuncaoTransferencia


# --------------------------------------------------------------------------- contorno
def _escala(L: FuncaoTransferencia) -> tuple[float, float]:
    raizes = np.concatenate([L.polos(), L.zeros()])
    mags = np.abs(raizes[np.abs(raizes) > 1e-9])
    alta = max([1.0] + list(mags))
    baixa = min([1.0] + list(mags))
    if L.atraso:
        alta = max(alta, 1.0 / L.atraso)
        baixa = min(baixa, 1.0 / L.atraso)
    return baixa, alta


def _polos_no_eixo(L: FuncaoTransferencia, tol=1e-7) -> np.ndarray:
    p = L.polos()
    w = np.sort(p[np.abs(p.real) < tol].imag)
    # remove duplicatas (polos múltiplos)
    if w.size:
        w = w[np.concatenate([[True], np.diff(w) > tol])]
    return w


def _segmentos(L: FuncaoTransferencia, R: float, eps: float, w0: float):
    """Lista de funções t∈[0,1] -> s que compõem o contorno, em ordem."""
    eixo = _polos_no_eixo(L)
    segs = []
    # pontos de parada no eixo imaginário: reta até jω_k - jε, indentação até jω_k + jε
    marcos = [-R]
    for wk in eixo:
        marcos += [wk - eps, ("indent", wk)]
    marcos.append(R)

    def reta(wa, wb):
        ua, ub = np.arcsinh(wa / w0), np.arcsinh(wb / w0)    # espaçamento ~log
        return lambda t: 1j * w0 * np.sinh(ua + (ub - ua) * t)

    def indent(wk):
        return lambda t: 1j * wk + eps * np.exp(1j * (-np.pi / 2 + np.pi * t))

    atual = marcos[0]
    for m in marcos[1:]:
        if isinstance(m, tuple):
            segs.append(("indentacao", indent(m[1])))
            atual = m[1] + eps
            continue
        segs.append(("eixo", reta(atual, m)))
        atual = m
    # semicírculo de raio R, de +jR a -jR passando por +R (horário)
    segs.append(("arco", lambda t: R * np.exp(1j * (np.pi / 2 - np.pi * t))))
    return segs


def _amostrar_adaptativo(f, seg, n0=64, passo_max=0.15, max_pts=200_000):
    """Amostra seg(t) e F = f(seg(t)) refinando onde arg F varia muito."""
    t = np.linspace(0.0, 1.0, n0)
    s = seg(t)
    F = f(s)
    avals = len(t)
    while True:
        dang = np.abs(np.angle(F[1:] / F[:-1]))
        ruim = np.flatnonzero(dang > passo_max)
        if ruim.size == 0 or len(t) > max_pts:
            break
        tm = 0.5 * (t[ruim] + t[ruim + 1])
        sm = seg(tm)
        Fm = f(sm)
        avals += len(tm)
        t = np.insert(t, ruim + 1, tm)
        s = np.insert(s, ruim + 1, sm)
        F = np.insert(F, ruim + 1, Fm)
    return t, s, F, avals


@dataclass
class ResultadoNyquist:
    P: int                 # polos instáveis de malha aberta
    N: int                 # voltas HORÁRIAS em torno de -1
    Z: int                 # polos instáveis de malha fechada (Z = N + P)
    estavel: bool
    s: np.ndarray          # contorno amostrado
    L: np.ndarray          # L(s) ao longo do contorno
    tipo: np.ndarray       # rótulo de cada ponto ('eixo', 'indentacao', 'arco')
    voltas_reais: float    # valor não arredondado (diagnóstico numérico)
    n_avaliacoes: int

    def resumo(self) -> str:
        return (f"P={self.P}  N={self.N}  Z=N+P={self.Z}  -> "
                f"{'ESTÁVEL' if self.estavel else 'INSTÁVEL'} "
                f"(voltas={self.voltas_reais:+.4f}, {self.n_avaliacoes} avaliações)")


def criterio_nyquist(L: FuncaoTransferencia, R: float | None = None,
                     passo_max: float = 0.15) -> ResultadoNyquist:
    baixa, alta = _escala(L)
    if R is None:
        R = 1e4 * alta
    eixo = _polos_no_eixo(L)
    sep = np.min(np.diff(eixo)) if eixo.size > 1 else 1.0
    eps = 1e-4 * min(baixa, sep, 1.0)
    w0 = 1e-2 * baixa

    f = lambda s: 1.0 + L(s)
    ss, FF, tt = [], [], []
    total = 0
    for nome, seg in _segmentos(L, R, eps, w0):
        _, s, F, n = _amostrar_adaptativo(f, seg, passo_max=passo_max)
        total += n
        ss.append(s); FF.append(F); tt += [nome] * len(s)
    s = np.concatenate(ss)
    F = np.concatenate(FF)
    # fecha a curva (último ponto do arco = primeiro ponto do eixo = -jR)
    Fc = np.append(F, F[0])
    voltas = np.sum(np.angle(Fc[1:] / Fc[:-1])) / (2 * np.pi)
    w = int(np.round(voltas))
    N = -w
    P = L.polos_instaveis_ma()
    Z = N + P
    return ResultadoNyquist(P, N, Z, Z == 0, s, F - 1.0, np.array(tt), voltas, total)


# --------------------------------------------------------------------- margens
def fase_continua(L: FuncaoTransferencia, w: np.ndarray) -> np.ndarray:
    """Fase de L(jω) em rad SEM ambiguidade de 2π.

    arg L(jω) = arg K + Σ arg(jω - z_i) - Σ arg(jω - p_i) - ωτ.
    Cada parcela é contínua em ω (exceto raízes sobre o eixo jω), logo a soma
    dispensa 'unwrap' – essencial para o termo de atraso -ωτ, que cresce sem limite.
    """
    w = np.asarray(w, dtype=float)
    jw = 1j * w
    k = L.num[0] / L.den[0]
    fase = np.full_like(w, 0.0 if k > 0 else np.pi)
    for z in L.zeros():
        fase += np.angle(jw - z)
    for p in L.polos():
        fase -= np.angle(jw - p)
    fase -= w * L.atraso
    return fase


def _bissecao(g, a, b, tol=1e-12, it=200):
    ga = g(a)
    for _ in range(it):
        m = np.sqrt(a * b)          # bisseção em escala log
        gm = g(m)
        if np.sign(gm) == np.sign(ga):
            a, ga = m, gm
        else:
            b = m
        if b / a - 1 < tol:
            break
    return np.sqrt(a * b)


@dataclass
class Margens:
    mg: float          # margem de ganho (absoluta); inf se não houver cruzamento de fase
    mg_db: float
    w_pc: float        # freq. de cruzamento de fase (-180°)
    mf: float          # margem de fase [graus]
    w_gc: float        # freq. de cruzamento de ganho (|L|=1)
    margem_atraso: float   # atraso adicional tolerável [s] = MF(rad)/w_gc
    todas_mg: list = field(default_factory=list)
    todas_mf: list = field(default_factory=list)


def margens_estabilidade(L: FuncaoTransferencia, n=6000) -> Margens:
    baixa, alta = _escala(L)
    w = np.logspace(np.log10(baixa) - 4, np.log10(alta) + 4, n)
    logmag = lambda x: np.log(np.abs(L.resposta_frequencia(x)))
    fase = lambda x: fase_continua(L, x)

    # --- cruzamentos de ganho |L| = 1
    lm = logmag(w)
    idx = np.flatnonzero(np.sign(lm[1:]) != np.sign(lm[:-1]))
    mfs = []
    for i in idx:
        wc = _bissecao(logmag, w[i], w[i + 1])
        ph = np.degrees(fase(np.array([wc]))[0])
        mf = (ph + 180.0 + 180.0) % 360.0 - 180.0    # em (-180, 180]
        mfs.append((mf, wc))

    # --- cruzamentos de fase  arg L = -180° + 360°k
    h = lambda x: (fase(np.atleast_1d(x)) + np.pi) / (2 * np.pi)
    hv = h(w)
    k = np.floor(hv)
    idx = np.flatnonzero(k[1:] != k[:-1])
    mgs = []
    for i in idx:
        alvo = max(k[i], k[i + 1])
        g = lambda x, alvo=alvo: h(x)[0] - alvo
        wp = _bissecao(g, w[i], w[i + 1])
        mag = np.abs(L.resposta_frequencia(wp))
        if mag > 1e-8:
            mgs.append((1.0 / mag, wp))

    # cruzamento em ω = 0: L(0) real e negativo (típico de planta instável, P > 0)
    if abs(L.den[-1]) > 1e-12:
        l0 = L.num[-1] / L.den[-1]
        if l0 < 0:
            mgs.append((1.0 / abs(l0), 0.0))

    if mgs:
        # margem relevante: a mais próxima de 0 dB (pior caso)
        mg, wpc = min(mgs, key=lambda t: abs(np.log(t[0])))
    else:
        mg, wpc = np.inf, np.nan
    if mfs:
        mf, wgc = min(mfs, key=lambda t: t[0])
    else:
        mf, wgc = np.inf, np.nan
    dm = np.radians(mf) / wgc if np.isfinite(mf) and mf > 0 else (0.0 if np.isfinite(mf) else np.inf)
    return Margens(mg, 20 * np.log10(mg) if np.isfinite(mg) else np.inf, wpc,
                   mf, wgc, dm, mgs, mfs)


def atraso_critico(L: FuncaoTransferencia) -> float:
    """Maior atraso total τ para o qual a malha fechada permanece estável (sistema
    estável em MA, sem atraso inicial conhecido): τ_crit = τ_atual + MF/ω_gc."""
    m = margens_estabilidade(L)
    return L.atraso + m.margem_atraso
