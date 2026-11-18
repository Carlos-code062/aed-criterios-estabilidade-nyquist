# Análise Computacional e Comparativa de Critérios de Estabilidade

Projeto de Pesquisa Aplicada — AED — Turma CP A01 — Prof. Nilson Cardoso Amaral
Trilha: Ciência da Computação (CC)

**Autores:** Carlos Eduardo Barbosa Pereira · Luiz Eduardo Santana Farias

Implementação **do zero** (apenas NumPy) do critério de estabilidade de Nyquist, comparado com
Routh–Hurwitz, Lugar das Raízes e Diagrama de Bode, em quatro sistemas de referência
(estável, instável em malha aberta, fase não-mínima e com atraso de transporte).

## Estrutura

```
estabilidade/          pacote principal (sem toolboxes de controle)
  polinomios.py        Horner, produto, derivada, raízes (matriz companheira, Durand–Kerner)
  sistema.py           L(s) = K·N(s)/D(s)·e^(−τs)
  nyquist.py           contorno com indentações, amostragem adaptativa, Z = N + P, margens
  routh.py             tabela de Routh (float ou exata), casos especiais, faixa de K
  lugar_raizes.py      lugar das raízes com passo adaptativo e regras geométricas
  bode.py              Bode exato e assintótico
  pade.py              aproximação de Padé de ordem n
  simulacao.py         degrau em malha fechada com atraso exato (RK4)
  sistemas_benchmark.py   sistemas A, B, C, D
tests/                 suíte pytest (28 testes, inclui validação cruzada com python-control)
experimentos.py        gera figuras/ e resultados/resultados.json
gerar_artigo.py        gera o artigo IEEE (.docx) a partir dos resultados
app/index.html         aplicação web interativa (trilha CC) — abrir direto no navegador
```

## Como reproduzir

```bash
pip install -r requirements.txt
python -m pytest -q tests          # 28 testes
python experimentos.py             # figuras + resultados (≈1 min)
python gerar_artigo.py             # Artigo_Criterios_Estabilidade_Nyquist.docx
```

A aplicação interativa não precisa de instalação: abra `app/index.html` no navegador
(ou `python -m http.server -d app` e acesse http://localhost:8000).

## Exemplo de uso

```python
from estabilidade import criterio_nyquist, margens_estabilidade
from estabilidade.sistemas_benchmark import sistema_D

L = sistema_D()                       # 2 e^(−0,5s) / ((s+1)(0,5s+1))
print(criterio_nyquist(L).resumo())   # P=0 N=0 Z=0 -> ESTÁVEL
m = margens_estabilidade(L)
print(m.mg, m.mf, m.margem_atraso)    # 1,879  55,13°  0,723 s
```

## Principais resultados

| Sistema | P | N | Z | MG | MF |
|---|---|---|---|---|---|
| A — 3ª ordem estável | 0 | 0 | 0 | 2,52 (8,03 dB) | 32,35° |
| B — pêndulo invertido + avanço | 1 | −1 | 0 | 0,40 (−7,96 dB) | 45,46° |
| C — fase não-mínima + integrador | 0 | 0 | 0 | 2,50 (7,96 dB) | 54,60° |
| D — atraso de 0,5 s | 0 | 0 | 0 | 1,88 (5,48 dB) | 55,13° |

* Margens idênticas às do python-control (diferença < 1e-10).
* Sistema D: Nyquist dá K_crit = 3,7580 e τ_crit = 1,2229 s exatos; Padé 1 + Routh erra 8,9 % e 30 %.
* Escalabilidade (n = 5…40): Routh é o mais barato; raízes por matriz companheira chegam a erro
  relativo de 0,29 em n = 40; Nyquist adaptativo usa ~250 avaliações de L(s) em qualquer ordem.
