"""Suíte de testes unitários (pytest).

Os valores de referência vêm de solução analítica (Routh feito à mão) e, quando
python-control estiver instalado, de validação cruzada com essa biblioteca.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from estabilidade import (FuncaoTransferencia, criterio_nyquist, margens_estabilidade,  # noqa: E402
                          tabela_routh, faixa_ganho, lugar_das_raizes, substituir_atraso,
                          atraso_critico, pade)
from estabilidade import polinomios as P  # noqa: E402
from estabilidade.sistemas_benchmark import sistema_A, sistema_B, sistema_C, sistema_D  # noqa: E402
from estabilidade.simulacao import degrau_malha_fechada  # noqa: E402



# ------------------------------------------------------------------ polinômios
def test_raizes_companheira():
    r = np.sort_complex(P.raizes(P.de_raizes([-1, -2, -3, 4])))
    assert np.allclose(r, np.sort_complex(np.array([-3, -2, -1, 4], dtype=complex)))


def test_durand_kerner_equivale_companheira():
    p = P.de_raizes([-1, -2 + 1j, -2 - 1j, -5])
    a = np.sort_complex(P.raizes(p)); b = np.sort_complex(P.durand_kerner(p))
    assert np.allclose(a, b, atol=1e-8)


def test_horner():
    assert P.horner([1, 3, 2], 2.0) == 12


# ---------------------------------------------------------------------- Routh
@pytest.mark.parametrize("k,esperado", [(50, True), (125.9, True), (126.1, False), (500, False)])
def test_routh_sistema_A(k, esperado):
    assert tabela_routh(sistema_A(k).polinomio_caracteristico()).estavel == esperado


def test_routh_conta_raizes_spd():
    # (s-1)(s-2)(s+3): duas raízes no SPD -> duas trocas de sinal
    assert tabela_routh(P.de_raizes([1, 2, -3])).trocas_sinal == 2


def test_routh_zero_primeira_coluna():
    # s^4 + s^3 + 2s^2 + 2s + 3 -> zero na 1ª coluna; 2 raízes no SPD
    r = tabela_routh([1, 1, 2, 2, 3])
    assert r.zero_primeira_coluna and r.trocas_sinal == 2


def test_routh_linha_nula():
    # (s^2+1)(s+2)(s+3): raízes ±j -> linha nula, marginalmente estável
    r = tabela_routh(P.de_raizes([1j, -1j, -2, -3]))
    assert r.linha_nula and r.marginal and not r.estavel and r.trocas_sinal == 0


def test_routh_exato_igual_float():
    p = P.de_raizes([-1, -2, -3, -4, -5])
    a = tabela_routh(p).primeira_coluna
    b = [float(x) for x in tabela_routh(p, exato=True).primeira_coluna]
    assert np.allclose(a, b)


def test_faixa_ganho():
    (a, b), = faixa_ganho([1.0], P.de_raizes([-1, -2, -5]))
    assert a == 0.0 and abs(b - 126) < 1e-6
    (a, b), = faixa_ganho([1.0, 1.0], P.de_raizes([2, -2, -10]))
    assert abs(a - 40) < 1e-6 and b == np.inf


# -------------------------------------------------------------------- Nyquist
@pytest.mark.parametrize("fab,P_esp,N_esp", [(sistema_A, 0, 0), (sistema_B, 1, -1),
                                             (sistema_C, 0, 0), (sistema_D, 0, 0)])
def test_nyquist_benchmarks_estaveis(fab, P_esp, N_esp):
    r = criterio_nyquist(fab())
    assert (r.P, r.N, r.Z, r.estavel) == (P_esp, N_esp, 0, True)
    assert abs(r.voltas_reais - round(r.voltas_reais)) < 1e-6


@pytest.mark.parametrize("fab,k_inst,Z_esp", [(sistema_A, 200, 2), (sistema_B, 20, 1), (sistema_C, 8, 2)])
def test_nyquist_detecta_instabilidade(fab, k_inst, Z_esp):
    L = fab(k_inst)
    r = criterio_nyquist(L)
    n_spd = int(np.sum(P.raizes(L.polinomio_caracteristico()).real > 0))
    assert r.Z == n_spd == Z_esp and not r.estavel


def test_nyquist_concorda_com_routh_em_varredura():
    for k in np.linspace(1, 200, 40):
        L = sistema_A(k)
        assert criterio_nyquist(L).estavel == tabela_routh(L.polinomio_caracteristico()).estavel


def test_nyquist_atraso_instavel():
    # atraso acima do crítico (≈1,223 s) deve instabilizar
    assert not criterio_nyquist(sistema_D(tau=1.3)).estavel
    assert criterio_nyquist(sistema_D(tau=1.15)).estavel


# -------------------------------------------------------------------- margens
def test_margens_sistema_A_analitico():
    m = margens_estabilidade(sistema_A(50))
    assert abs(m.mg - 126 / 50) < 1e-6           # K_crit/K
    assert abs(m.w_pc - np.sqrt(17)) < 1e-6      # ω de oscilação pelo Routh


def test_atraso_critico_consistente():
    tc = atraso_critico(sistema_D())
    m = margens_estabilidade(sistema_D(tau=tc))
    assert abs(m.mf) < 1e-3


# ----------------------------------------------------------------------- Padé
def test_pade_converge_para_kcrit_exato():
    L = sistema_D()
    k_exato = 2 * margens_estabilidade(L).mg
    erros = []
    for o in (1, 2, 3, 5):
        Lp = substituir_atraso(L, o)
        (_, kc), = faixa_ganho(Lp.com_ganho(0.5).num, Lp.den)
        erros.append(abs(kc - k_exato) / k_exato)
    assert all(erros[i + 1] < erros[i] for i in range(len(erros) - 1))
    assert erros[-1] < 1e-6


def test_pade_ordem1():
    num, den = pade(2.0, 1)
    assert np.allclose(num, [-1, 1]) and np.allclose(den, [1, 1])


# ---------------------------------------------------------------- Lugar raízes
def test_lugar_raizes_regras():
    lr = lugar_das_raizes(FuncaoTransferencia([1.0], P.de_raizes([-1, -2, -5])))
    assert abs(lr.centroide + 8 / 3) < 1e-9
    assert np.allclose(lr.angulos_assintotas, [60, 180, 300])
    kc, wc = lr.cruzamentos_jw[0]
    assert abs(kc - 126) < 1e-4 and abs(wc - np.sqrt(17)) < 1e-4


# ------------------------------------------------------------------ simulação
def test_degrau_valor_final():
    _, y = degrau_malha_fechada(sistema_A(50), 25)
    assert abs(y[-1] - 50 / 60) < 1e-3


# ----------------------------------------------------- validação cruzada (opcional)
def test_validacao_cruzada_python_control():
    ct = pytest.importorskip("control")
    for fab in (sistema_A, sistema_B, sistema_C):
        L = fab()
        gm, pm, *_ = ct.stability_margins(ct.tf(L.num, L.den))
        m = margens_estabilidade(L)
        assert abs(m.mg - gm) < 1e-6 and abs(m.mf - pm) < 1e-6
        polos_ref = np.sort_complex(ct.poles(ct.feedback(ct.tf(L.num, L.den), 1)))
        assert np.allclose(np.sort_complex(L.polos_malha_fechada()), polos_ref, atol=1e-8)
