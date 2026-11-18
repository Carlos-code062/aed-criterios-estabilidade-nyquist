"""Análise computacional e comparativa de critérios de estabilidade.

Módulos implementados sem toolboxes de controle (apenas NumPy):
nyquist, routh, lugar_raizes, bode, pade, simulacao.
"""
from .sistema import FuncaoTransferencia
from .nyquist import criterio_nyquist, margens_estabilidade, atraso_critico
from .routh import tabela_routh, faixa_ganho
from .lugar_raizes import lugar_das_raizes
from .bode import bode, bode_assintotico
from .pade import pade, substituir_atraso
from . import sistemas_benchmark

__all__ = [
    "FuncaoTransferencia", "criterio_nyquist", "margens_estabilidade", "atraso_critico",
    "tabela_routh", "faixa_ganho", "lugar_das_raizes", "bode", "bode_assintotico",
    "pade", "substituir_atraso", "sistemas_benchmark",
]
