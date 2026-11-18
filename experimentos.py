"""Gera todas as figuras e tabelas do artigo (Fases 3 e 4 – validação e benchmarking).

Uso:  python experimentos.py
Saídas: figuras/*.png  e  resultados/resultados.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from estabilidade import (FuncaoTransferencia, criterio_nyquist, margens_estabilidade, tabela_routh,
                          faixa_ganho, lugar_das_raizes, bode, bode_assintotico, substituir_atraso,
                          atraso_critico)
from estabilidade import polinomios as P
from estabilidade.sistemas_benchmark import sistema_A, sistema_B, sistema_C, sistema_D, TODOS
from estabilidade.simulacao import degrau_malha_fechada

RAIZ = Path(__file__).parent
FIG = RAIZ / "figuras"; FIG.mkdir(exist_ok=True)
RES = RAIZ / "resultados"; RES.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 150, "axes.grid": True, "grid.alpha": 0.3,
                     "savefig.bbox": "tight"})
COR = ["#1f4e79", "#c0392b", "#16a085", "#8e44ad", "#d35400"]
resultados: dict = {}


def cronometrar(f, rep=5):
    melhores = []
    for _ in range(rep):
        t0 = time.perf_counter(); out = f(); melhores.append(time.perf_counter() - t0)
    return min(melhores), out


# ------------------------------------------------------------- 1. sistemas A–D
def analise_benchmarks():
    tab = {}
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 6.2))
    for ax, (nome, fab) in zip(axs.flat, TODOS.items()):
        L = fab()
        r = criterio_nyquist(L)
        m = margens_estabilidade(L)
        # traçado denso apenas para visualização (o veredito vem do contorno adaptativo)
        w = np.logspace(-3, 2.5, 6000)
        Lw = L.resposta_frequencia(w)
        ax.plot(Lw.real, Lw.imag, color=COR[0], lw=1.3, label="ω > 0")
        ax.plot(Lw.real, -Lw.imag, "--", color=COR[0], lw=0.9, alpha=0.6, label="ω < 0")
        ax.plot(-1, 0, "x", color=COR[1], ms=8, mew=2)
        ax.set_title(f"Sistema {nome}: P={r.P}, N={r.N}, Z={r.Z}", fontsize=9)
        ax.set_xlabel("Re{L(jω)}"); ax.set_ylabel("Im{L(jω)}")
        ax.axhline(0, color="k", lw=0.5); ax.axvline(0, color="k", lw=0.5)
        limites = {"A": ((-1.5, 5.5), (-3.5, 3.5)), "B": ((-3, 1), (-2.5, 2.5)),
                   "C": ((-2.5, 1), (-3, 3)), "D": ((-1.5, 2.3), (-1.7, 1.7))}
        ax.set_xlim(*limites[nome][0]); ax.set_ylim(*limites[nome][1])
        ax.legend(fontsize=7, loc="best")
        info = {"P": r.P, "N": r.N, "Z": r.Z, "estavel": r.estavel, "avaliacoes": r.n_avaliacoes,
                "MG": m.mg, "MG_dB": m.mg_db, "w_pc": m.w_pc, "MF": m.mf, "w_gc": m.w_gc,
                "margem_atraso": m.margem_atraso}
        if not L.atraso:
            rt = tabela_routh(L.polinomio_caracteristico())
            info["routh"] = rt.resumo()
            info["polos_mf"] = [str(np.round(p, 4)) for p in L.polos_malha_fechada()]
            info["faixa_K"] = [[a, (b if np.isfinite(b) else "inf")] for a, b in
                               faixa_ganho(fab(1.0).num, L.den)]
        else:
            info["routh"] = "não aplicável sem aproximação de Padé"
        tab[nome] = info
    fig.tight_layout(); fig.savefig(FIG / "fig_nyquist_ABCD.png"); plt.close(fig)
    resultados["benchmarks"] = tab


# ----------------------------------------------------------------- 2. Bode
def figura_bode():
    fig, axs = plt.subplots(2, 1, figsize=(3.6, 4.4), sharex=True)
    for i, nome in enumerate("ACD"):
        L = TODOS[nome]()
        w, mag, fase = bode(L, np.logspace(-2, 2, 1500))
        axs[0].semilogx(w, mag, color=COR[i], label=f"{nome}")
        if nome == "A":
            axs[0].semilogx(w, bode_assintotico(L, w), ":", color=COR[i], lw=1, label="A (assint.)")
        axs[1].semilogx(w, fase, color=COR[i])
    axs[0].axhline(0, color="k", lw=0.6); axs[1].axhline(-180, color="k", lw=0.6)
    axs[0].set_ylabel("|L(jω)| [dB]"); axs[1].set_ylabel("fase [°]"); axs[1].set_xlabel("ω [rad/s]")
    axs[0].set_ylim(-60, 40); axs[1].set_ylim(-540, 0)
    axs[0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig_bode.png"); plt.close(fig)


# ------------------------------------------------------------ 3. Lugar das raízes
def figura_lugar():
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    for ax, nome in zip(axs, "ABC"):
        L = TODOS[nome](1.0)
        t, lr = cronometrar(lambda: lugar_das_raizes(L), rep=1)
        for j in range(lr.ramos.shape[1]):
            r = lr.ramos[:, j]
            ok = np.abs(r) < 30
            ax.plot(r.real[ok], r.imag[ok], color=COR[j % len(COR)], lw=1.1)
        ax.plot(L.polos().real, L.polos().imag, "x", color="k", ms=6)
        if len(L.zeros()):
            ax.plot(L.zeros().real, L.zeros().imag, "o", mfc="none", color="k", ms=6)
        for kc, wc in lr.cruzamentos_jw:
            ax.plot([0, 0], [wc, -wc], "s", color=COR[1], ms=4)
        ax.axvline(0, color="k", lw=0.6)
        ax.set_xlim(-12, 4); ax.set_ylim(-8, 8)
        ax.set_title(f"{nome}: K_jω = " + ", ".join(f"{k:.4g}" for k, _ in lr.cruzamentos_jw), fontsize=8)
        ax.set_xlabel("Re{s}")
        resultados.setdefault("lugar_raizes", {})[nome] = {
            "centroide": lr.centroide, "assintotas": lr.angulos_assintotas.tolist(),
            "separacao": lr.pontos_separacao.tolist(), "cruzamentos_jw": lr.cruzamentos_jw,
            "pontos_K": len(lr.ganhos), "raizes_calculadas": lr.n_raizes_calculadas, "tempo_s": t}
    axs[0].set_ylabel("Im{s}")
    fig.tight_layout(); fig.savefig(FIG / "fig_lugar_raizes.png"); plt.close(fig)


# -------------------------------------------------------------- 4. Atraso × Padé
def atraso_vs_pade():
    L = sistema_D()
    m = margens_estabilidade(L)
    k_exato = 2.0 * m.mg
    tau_exato = atraso_critico(L)
    linhas = []
    for o in (1, 2, 3, 4, 5, 8):
        Lp = substituir_atraso(L, o)
        (_, kc), = faixa_ganho(Lp.com_ganho(0.5).num, Lp.den)
        # τ crítico via Padé + Routh: bisseção em τ
        a, b = 0.1, 3.0
        for _ in range(60):
            c = 0.5 * (a + b)
            Lc = substituir_atraso(sistema_D(tau=c), o)
            if tabela_routh(Lc.polinomio_caracteristico()).estavel:
                a = c
            else:
                b = c
        linhas.append({"ordem": o, "K_crit": kc, "erro_K_%": 100 * abs(kc - k_exato) / k_exato,
                       "tau_crit": a, "erro_tau_%": 100 * abs(a - tau_exato) / tau_exato,
                       "grau_polinomio": P.grau(Lp.polinomio_caracteristico())})
    resultados["atraso"] = {"K_crit_exato": k_exato, "tau_crit_exato": tau_exato,
                            "MF": m.mf, "w_gc": m.w_gc, "pade": linhas}
    # figura: Nyquist exato x Padé 1, e respostas ao degrau
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    w = np.logspace(-2, 1.3, 3000)
    axs[0].plot(L.resposta_frequencia(w).real, L.resposta_frequencia(w).imag, color=COR[0], label=r"exato $e^{-\tau s}$")
    for o, c, ls in ((1, COR[1], "--"), (2, COR[2], ":")):
        Lp = substituir_atraso(L, o)
        axs[0].plot(Lp.resposta_frequencia(w).real, Lp.resposta_frequencia(w).imag, ls, color=c, label=f"Padé {o}")
    axs[0].plot(-1, 0, "x", color="k", ms=7, mew=2)
    axs[0].set_xlim(-1.5, 2.2); axs[0].set_ylim(-2, 1); axs[0].legend(fontsize=7)
    axs[0].set_title("Sistema D: Nyquist exato × Padé", fontsize=9)
    for tau, c in ((0.5, COR[0]), (1.0, COR[2]), (tau_exato, COR[3]), (1.4, COR[1])):
        t, y = degrau_malha_fechada(sistema_D(tau=tau), 30, dt=2e-3, limite=50)
        axs[1].plot(t, y, color=c, lw=1, label=f"τ = {tau:.3f} s")
    axs[1].set_ylim(-1.5, 3); axs[1].set_xlabel("t [s]"); axs[1].set_ylabel("y(t)")
    axs[1].set_title("Degrau em malha fechada (atraso exato)", fontsize=9)
    axs[1].legend(fontsize=7, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "fig_atraso_pade.png"); plt.close(fig)


# ----------------------------------------------------- 5. Escalabilidade numérica
def sistema_aleatorio(n, rng):
    raizes = []
    while len(raizes) < n:
        if n - len(raizes) >= 2 and rng.random() < 0.5:
            re, im = -rng.uniform(0.2, 5), rng.uniform(0.5, 5)
            raizes += [re + 1j * im, re - 1j * im]
        else:
            raizes.append(-rng.uniform(0.2, 5))
    D = P.de_raizes(raizes)
    return np.real(D), np.array(raizes)


def escalabilidade():
    rng = np.random.default_rng(2026)
    ordens = [5, 10, 20, 30, 40]
    linhas = []
    for n in ordens:
        tempos = {k: [] for k in ("routh", "routh_exato", "raizes_eig", "durand_kerner", "nyquist", "bode",
                                  "lugar_raizes")}
        erros_raiz, erros_routh = [], []
        acertos = {"routh": 0, "raizes": 0, "nyquist": 0}
        avals = []
        n_amostras = 30 if n <= 20 else 15
        for _ in range(n_amostras):
            D, rr = sistema_aleatorio(n, rng)
            # ganho escolhido para que o sistema em MF fique perto da fronteira (caso difícil)
            K = abs(D[-1]) * rng.uniform(0.5, 3.0)
            L = FuncaoTransferencia([K], D)
            car = L.polinomio_caracteristico()
            t, rt_ex = cronometrar(lambda: tabela_routh(car, exato=True), rep=1)
            tempos["routh_exato"].append(t)
            verdade = rt_ex.estavel
            t, rt = cronometrar(lambda: tabela_routh(car)); tempos["routh"].append(t)
            col_ex = np.array([float(x) for x in rt_ex.primeira_coluna])
            col = np.array(rt.primeira_coluna, dtype=float)
            if len(col) == len(col_ex):
                erros_routh.append(np.max(np.abs(col - col_ex) / np.maximum(np.abs(col_ex), 1e-300)))
            acertos["routh"] += rt.estavel == verdade
            t, raizes_mf = cronometrar(lambda: P.raizes(car)); tempos["raizes_eig"].append(t)
            acertos["raizes"] += bool(np.all(raizes_mf.real < 0)) == verdade
            t, _ = cronometrar(lambda: P.durand_kerner(D), rep=1); tempos["durand_kerner"].append(t)
            # erro das raízes de MA (conhecidas exatamente)
            r_calc = P.raizes(D)
            erros_raiz.append(max(np.min(np.abs(r_calc - r)) / abs(r) for r in rr))
            t, ny = cronometrar(lambda: criterio_nyquist(L), rep=3); tempos["nyquist"].append(t)
            avals.append(ny.n_avaliacoes)
            acertos["nyquist"] += ny.estavel == verdade
            wb = np.logspace(-2, 2, 1000)
            t, _ = cronometrar(lambda: bode(L, wb)); tempos["bode"].append(t)
            if n <= 20:
                t, _ = cronometrar(lambda: lugar_das_raizes(L.com_ganho(1 / K), k_max=10 * K, dmax=0.05,
                                                            max_pts=1500), rep=1)
                tempos["lugar_raizes"].append(t)
        linhas.append({"n": n, "amostras": n_amostras,
                       **{f"t_{k}_ms": (1e3 * float(np.median(v)) if v else None) for k, v in tempos.items()},
                       "erro_rel_raizes_MA": float(np.median(erros_raiz)),
                       "erro_rel_routh_max": float(np.max(erros_routh)) if erros_routh else None,
                       "erro_rel_routh_mediana": float(np.median(erros_routh)) if erros_routh else None,
                       "acerto_routh_%": 100 * acertos["routh"] / n_amostras,
                       "acerto_raizes_%": 100 * acertos["raizes"] / n_amostras,
                       "acerto_nyquist_%": 100 * acertos["nyquist"] / n_amostras,
                       "avaliacoes_nyquist": float(np.median(avals))})
        print(f"  n={n}: ok")
    resultados["escalabilidade"] = linhas

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    ns = [l["n"] for l in linhas]
    for k, lab, c in (("routh", "Routh (float)", COR[0]), ("raizes_eig", "Raízes (companheira)", COR[2]),
                      ("nyquist", "Nyquist (adaptativo)", COR[1]), ("bode", "Bode (1000 pts)", COR[3]),
                      ("lugar_raizes", "Lugar das raízes", COR[4]), ("routh_exato", "Routh (exato)", "gray")):
        ys = [l[f"t_{k}_ms"] for l in linhas]
        xs = [n for n, y in zip(ns, ys) if y is not None]; ys = [y for y in ys if y is not None]
        axs[0].semilogy(xs, ys, "o-", color=c, ms=3, label=lab)
    axs[0].set_xlabel("ordem n"); axs[0].set_ylabel("tempo mediano [ms]")
    axs[0].set_ylim(5e-3, 5e3); axs[0].legend(fontsize=6, ncol=2, loc="upper left")
    axs[1].semilogy(ns, [l["erro_rel_raizes_MA"] for l in linhas], "o-", color=COR[2], ms=3,
                    label="raízes (erro rel. mediano)")
    axs[1].semilogy(ns, [l["erro_rel_routh_mediana"] for l in linhas], "o-", color=COR[0], ms=3,
                    label="1ª col. Routh (mediano)")
    axs[1].semilogy(ns, [l["erro_rel_routh_max"] for l in linhas], "s--", color=COR[0], ms=3,
                    label="1ª col. Routh (máximo)")
    axs[1].set_xlabel("ordem n"); axs[1].set_ylabel("erro relativo"); axs[1].legend(fontsize=6)
    fig.tight_layout(); fig.savefig(FIG / "fig_escalabilidade.png"); plt.close(fig)


# ---------------------------------------------------- 6. Validação cruzada
def validacao_cruzada():
    try:
        import control as ct
    except ImportError:
        resultados["validacao"] = "python-control não instalado"
        return
    linhas = []
    for nome, fab in TODOS.items():
        L = fab()
        sysc = ct.tf(L.num, L.den)
        if L.atraso:
            sysc = sysc * ct.tf(*ct.pade(L.atraso, 20))
        gm, pm, _, wpc, wgc, _ = ct.stability_margins(sysc)
        m = margens_estabilidade(L)
        linhas.append({"sistema": nome, "MG_proprio": m.mg, "MG_control": float(gm),
                       "MF_proprio": m.mf, "MF_control": float(pm),
                       "dif_MG": abs(m.mg - gm), "dif_MF": abs(m.mf - pm),
                       "wgc_proprio": m.w_gc, "wgc_control": float(wgc)})
    resultados["validacao"] = linhas


if __name__ == "__main__":
    print("benchmarks A–D"); analise_benchmarks()
    print("Bode"); figura_bode()
    print("Lugar das raízes"); figura_lugar()
    print("Atraso × Padé"); atraso_vs_pade()
    print("Validação cruzada"); validacao_cruzada()
    print("Escalabilidade"); escalabilidade()
    (RES / "resultados.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False, default=str),
                                         encoding="utf-8")
    print("ok ->", RES / "resultados.json")
