"""Gera o artigo científico (formato IEEE, duas colunas) em .docx a partir de
resultados/resultados.json e das figuras em figuras/.  Uso: python gerar_artigo.py
"""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

RAIZ = Path(__file__).parent
R = json.loads((RAIZ / "resultados" / "resultados.json").read_text(encoding="utf-8"))
FIG = RAIZ / "figuras"
SAIDA = RAIZ / "Artigo_Criterios_Estabilidade_Nyquist.docx"

AUTORES = ["Carlos Eduardo Barbosa Pereira", "Luiz Eduardo Santana Farias"]

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"; st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(2)
st.paragraph_format.line_spacing = 1.0

sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(1.6)
sec.top_margin, sec.bottom_margin = Cm(1.9), Cm(2.5)


def colunas(secao, n):
    sp = secao._sectPr
    for c in sp.findall(qn("w:cols")):
        sp.remove(c)
    cols = OxmlElement("w:cols"); cols.set(qn("w:num"), str(n)); cols.set(qn("w:space"), "425")
    sp.append(cols)


def par(texto="", tam=10, negrito=False, italico=False, alin=WD_ALIGN_PARAGRAPH.JUSTIFY, antes=0, depois=2,
        recuo=True):
    p = doc.add_paragraph()
    p.alignment = alin
    p.paragraph_format.space_before = Pt(antes); p.paragraph_format.space_after = Pt(depois)
    if recuo and alin == WD_ALIGN_PARAGRAPH.JUSTIFY:
        p.paragraph_format.first_line_indent = Cm(0.35)
    if texto:
        rich(p, texto, tam, negrito, italico)
    return p


def rich(p, texto, tam=10, negrito=False, italico=False):
    """Suporta *itálico* e **negrito** simples dentro do texto."""
    import re
    partes = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", texto)
    for parte in partes:
        if not parte:
            continue
        b, i, t = negrito, italico, parte
        if parte.startswith("**"):
            b, t = True, parte[2:-2]
        elif parte.startswith("*"):
            i, t = True, parte[1:-1]
        # expoentes: x^(…) ou x^−12 / x^-12 / x^20 viram sobrescrito
        for k, pedaco in enumerate(re.split(r"\^(\([^)]*\)|[−-]?\d+)", t)):
            if not pedaco:
                continue
            sobrescrito = k % 2 == 1
            if sobrescrito:
                pedaco = pedaco.strip("()").replace("-", "−")
            r = p.add_run(pedaco); r.font.size = Pt(tam); r.bold = b; r.italic = i
            r.font.superscript = sobrescrito
    return p


SECAO = [0]
SUB = [0]


def secao(titulo):
    SECAO[0] += 1; SUB[0] = 0
    romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=8, depois=4, recuo=False)
    r = p.add_run(f"{romanos[SECAO[0] - 1]}. {titulo.upper()}"); r.font.size = Pt(10); r.font.small_caps = True


def subsecao(titulo):
    SUB[0] += 1
    p = par(alin=WD_ALIGN_PARAGRAPH.LEFT, antes=4, depois=2, recuo=False)
    r = p.add_run(f"{chr(64 + SUB[0])}. {titulo}"); r.italic = True; r.font.size = Pt(10)


def equacao(texto, num):
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c0, c1 = t.rows[0].cells
    c0.width, c1.width = Cm(7.2), Cm(1.0)
    p = c0.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rich(p, texto, 10, italico=True)
    p = c1.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"({num})").font.size = Pt(10)


FIGN = [0]
TABN = [0]


def figura(arquivo, legenda, largura=Cm(8.4)):
    FIGN[0] += 1
    p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=4, depois=0, recuo=False)
    p.add_run().add_picture(str(FIG / arquivo), width=largura)
    p = par(alin=WD_ALIGN_PARAGRAPH.JUSTIFY, depois=6, recuo=False)
    r = p.add_run(f"Fig. {FIGN[0]}. "); r.font.size = Pt(8)
    rich(p, legenda, 8)
    return FIGN[0]


def tabela(titulo, cab, linhas, larguras=None, tam=7.5):
    TABN[0] += 1
    romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=6, depois=0, recuo=False)
    r = p.add_run(f"TABELA {romanos[TABN[0] - 1]}"); r.font.size = Pt(8)
    p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, depois=2, recuo=False)
    r = p.add_run(titulo); r.font.size = Pt(8); r.font.small_caps = True
    t = doc.add_table(rows=1 + len(linhas), cols=len(cab))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for j, h in enumerate(cab):
        c = t.rows[0].cells[j]; c.text = ""
        rich(c.paragraphs[0], h, tam, negrito=True)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        sombra = OxmlElement("w:shd"); sombra.set(qn("w:fill"), "DCE3EC"); c._tc.get_or_add_tcPr().append(sombra)
    for i, linha in enumerate(linhas, 1):
        for j, v in enumerate(linha):
            c = t.rows[i].cells[j]; c.text = ""
            rich(c.paragraphs[0], str(v), tam)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
    if larguras:
        for row in t.rows:
            for c, w in zip(row.cells, larguras):
                c.width = Cm(w)
    par(depois=4, recuo=False)
    return TABN[0]


def f(v, d=3):
    if v in ("inf", None) or (isinstance(v, float) and v == float("inf")):
        return "∞"
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def g(v, d=3):
    s = f"{v:.{d}g}"
    if "e" in s:
        m, e = s.split("e"); s = f"{m}×10^{int(e)}"
    return s.replace(".", ",")


# ============================================================ cabeçalho (1 coluna)
p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=0, depois=6, recuo=False)
r = p.add_run("Análise Computacional e Comparativa de Critérios de Estabilidade em Sistemas Dinâmicos: "
              "Nyquist, Routh–Hurwitz, Lugar das Raízes e Bode")
r.font.size = Pt(20)
p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, depois=1, recuo=False)
rich(p, "     ".join(AUTORES), 11)
p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, depois=10, recuo=False)
rich(p, "*Projeto de Pesquisa Aplicada — AED — Turma CP A01 — Prof. Nilson Cardoso Amaral — Trilha Ciência da Computação (CC)*", 9)

sec2 = doc.add_section(WD_SECTION.CONTINUOUS)
colunas(doc.sections[0], 1)
colunas(sec2, 2)

# ============================================================ resumo
B = R["benchmarks"]; A = R["atraso"]; E = R["escalabilidade"]; V = R["validacao"]
pade = {l["ordem"]: l for l in A["pade"]}
e40 = E[-1]; e20 = [l for l in E if l["n"] == 20][0]
p = par(recuo=False)
r = p.add_run("Resumo—"); r.bold = True; r.italic = True; r.font.size = Pt(9)
rich(p, "*Este trabalho apresenta uma ferramenta em Python, construída apenas com NumPy, que implementa do zero o "
        "critério de estabilidade de Nyquist (contorno com indentações, amostragem adaptativa e contagem do "
        "número de voltas), o cálculo automático das margens de ganho, fase e atraso, a tabela de Routh–Hurwitz "
        "com os dois casos especiais, o traçado do lugar das raízes com passo adaptativo e o diagrama de Bode. "
        "Os métodos foram aplicados a quatro plantas de referência (estável, instável em malha aberta, fase "
        f"não-mínima e com atraso de transporte) e validados contra a biblioteca python-control, com diferenças "
        f"abaixo de 10^-10 nas margens. No sistema com atraso, Nyquist fornece o ganho crítico exato "
        f"K = {f(A['K_crit_exato'], 4)}, enquanto Routh com Padé de 1ª ordem erra {f(pade[1]['erro_K_%'], 1)}% "
        f"e superestima o atraso crítico em {f(pade[1]['erro_tau_%'], 1)}%. No estudo de escalabilidade "
        f"(n = 5 a 40) a tabela de Routh foi o método mais barato e numericamente robusto, desde que a detecção "
        f"de zeros seja relativa à escala de cada elemento; as raízes via matriz companheira chegaram a erro "
        f"relativo de {g(e40['erro_rel_raizes_MA'], 2)} em n = 40, e o Nyquist adaptativo manteve 100% de acerto com "
        f"cerca de {int(e40['avaliacoes_nyquist'])} avaliações de L(s). Uma aplicação web interativa completa a "
        "trilha CC.*", 9)
p = par(recuo=False, depois=6)
r = p.add_run("Palavras-chave—"); r.bold = True; r.italic = True; r.font.size = Pt(9)
rich(p, "*estabilidade, critério de Nyquist, princípio do argumento, Routh–Hurwitz, lugar das raízes, "
        "atraso de transporte, aproximação de Padé, métodos numéricos.*", 9)

# ============================================================ I. Introdução
secao("Introdução")
par("A análise de estabilidade é etapa obrigatória no projeto de sistemas de controle, robótica, sistemas "
    "embarcados e sistemas controlados via rede (*Networked Control Systems*). Métodos algébricos, como o "
    "critério de Routh–Hurwitz, respondem apenas se o sistema é estável; já o critério de Nyquist [1]–[4], por "
    "operar no domínio da frequência, informa também *quão* estável o sistema é (margens de ganho e fase) e "
    "trata de forma exata o atraso puro e^(−τs), que torna a equação característica transcendental.")
par("Para Ciência e Engenharia da Computação, o desafio não é apenas a teoria: é transformar cada critério em um "
    "algoritmo numérico correto, eficiente e robusto a erros de arredondamento. Este artigo descreve essa "
    "implementação (sem *toolboxes* de controle), valida-a contra bibliotecas consolidadas [5], [6] e compara "
    "empiricamente precisão, limitações e custo computacional dos quatro métodos.")
par("O texto está organizado assim: a Seção II resume a fundamentação; a Seção III descreve a arquitetura dos "
    "algoritmos; a Seção IV define as plantas de teste; a Seção V apresenta os resultados; a Seção VI consolida "
    "a análise comparativa e a Seção VII conclui.")

# ============================================================ II. Fundamentação
secao("Fundamentação Teórica")
subsecao("Mapeamento conforme e princípio do argumento")
par("Seja F(s) uma função racional e Γ um contorno fechado simples no plano s, percorrido no sentido horário, "
    "que não passa por polos nem zeros de F. O princípio do argumento de Cauchy afirma que a imagem F(Γ) "
    "envolve a origem, no sentido horário, um número de vezes")
equacao("N = Z − P", 1)
par("em que Z e P são, respectivamente, os zeros e os polos de F no interior de Γ. Como F é analítica fora de "
    "seus polos, o mapeamento é conforme e a contagem de voltas é um invariante topológico: depende apenas de "
    "quantas singularidades Γ envolve, não da forma exata do contorno.", recuo=False)
subsecao("Critério de estabilidade de Nyquist")
par("Na realimentação negativa unitária com função de malha aberta L(s) = G(s)H(s), os polos de malha fechada "
    "são os zeros de F(s) = 1 + L(s), e os polos de F coincidem com os de L. Escolhendo Γ como o *contorno de "
    "Nyquist* — o eixo jω de −jR a +jR fechado por um semicírculo de raio R → ∞ no semiplano direito (SPD) — "
    "e contando as voltas de L(Γ) em torno de −1 + j0 (equivalente às voltas de F em torno da origem):")
equacao("Z = N + P", 2)
par("Z é o número de polos de malha fechada no SPD, P o de polos de malha aberta no SPD e N o de voltas "
    "horárias em torno de −1. O sistema é estável se e somente se Z = 0; para P > 0 isso exige N = −P voltas "
    "anti-horárias. Polos de L sobre o eixo jω são contornados por semicírculos de raio ε → 0 pela direita.",
    recuo=False)
par("As margens de estabilidade relativa são lidas na mesma curva: a margem de ganho MG = 1/|L(jω_pc)| na "
    "frequência em que arg L = −180°, e a margem de fase MF = 180° + arg L(jω_gc) na frequência em que "
    "|L| = 1. Um atraso adicional Δτ gira a fase de −ωΔτ sem alterar o módulo; logo a margem de atraso é")
equacao("τ_max = MF [rad] / ω_gc", 3)
subsecao("Sistemas com atraso de transporte")
par("O atraso e^(−τs) tem |e^(−jωτ)| = 1 e fase −ωτ, de modo que L(jω) é calculado exatamente e o critério "
    "de Nyquist se aplica sem modificações. Métodos baseados em polinômios (Routh e lugar das raízes) exigem "
    "aproximá-lo por uma função racional; a mais usada é a de Padé [7] de ordem n:")
equacao("e^(−τs) ≈ Q(−τs)/Q(τs),  Q(x) = Σ c_k x^k,  c_k = (2n−k)! n! / [(2n)! k! (n−k)!]", 4)
par("A aproximação introduz n zeros no SPD e n polos no SPE, aumenta o grau do polinômio característico e "
    "só é fiel até frequências da ordem de n/τ.", recuo=False)
subsecao("Métodos alternativos clássicos")
par("**Routh–Hurwitz** conta as trocas de sinal da primeira coluna de uma tabela construída por determinantes "
    "2×2 dos coeficientes do polinômio característico; cada troca corresponde a uma raiz no SPD. Há dois casos "
    "especiais: um zero isolado na primeira coluna (substituído por ε) e uma linha inteira nula (substituída pela "
    "derivada do polinômio auxiliar, indicando raízes simétricas, possivelmente sobre o eixo jω). "
    "O **lugar das raízes** traça as raízes de D(s) + K N(s) = 0 para K ∈ [0, ∞), evidenciando o efeito do "
    "ganho no amortecimento e na frequência natural. O **diagrama de Bode** apresenta |L(jω)| em dB e arg L(jω) "
    "em escala logarítmica de frequência, com aproximações assintóticas que facilitam o projeto de "
    "compensadores; as margens obtidas por Bode e Nyquist são as mesmas, mas a interpretação direta de Bode "
    "falha quando P > 0.")

# ============================================================ III. Arquitetura
secao("Arquitetura dos Algoritmos")
par("A ferramenta é um pacote Python (*estabilidade/*) cujos módulos usam apenas arrays e álgebra linear do "
    "NumPy [6]; python-control e SciPy aparecem somente na suíte de validação. A Tabela I resume os módulos.")
tabela("Módulos implementados", ["Módulo", "Responsabilidade"], [
    ["polinomios", "Horner, produto, derivada, raízes (matriz companheira e Durand–Kerner)"],
    ["sistema", "L(s) = K·N(s)/D(s)·e^(−τs); avaliação, polos, zeros, P"],
    ["nyquist", "contorno, amostragem adaptativa, voltas, Z = N + P, margens"],
    ["routh", "tabela em float ou racional exata, casos especiais, faixa de K"],
    ["lugar_raizes", "passo adaptativo em K, ordenação de ramos, assíntotas, separação, cruzamento jω"],
    ["bode, pade", "resposta em frequência, assíntotas; aproximação de Padé de ordem n"],
    ["simulacao", "degrau em malha fechada com atraso exato (RK4 + buffer)"],
], [2.2, 6.2])

subsecao("Contorno de Nyquist e contagem de voltas")
par("O contorno é composto por segmentos parametrizados por t ∈ [0, 1]: trechos retos do eixo jω, "
    "semicírculos de raio ε = 10^−4·ω_min à direita de cada polo sobre o eixo, e o arco de raio "
    "R = 10^4·ω_max. Nos trechos retos usa-se ω = ω₀ sinh(u), com u uniforme, o que dá espaçamento "
    "aproximadamente logarítmico em ambos os sentidos de ω sem tratar ω = 0 à parte.")
par("O ponto central é a **amostragem adaptativa**: cada segmento começa com 64 pontos e, enquanto existir par "
    "consecutivo com |Δ arg F| > 0,15 rad, insere-se o ponto médio do parâmetro. Garantido |Δ arg F| < π entre "
    "vizinhos, a soma")
equacao("w = (1/2π) Σ_k arg(F_(k+1)/F_k),   N = −w", 5)
par("é exata (sem ambiguidade de 2π) e o desvio de w em relação ao inteiro mais próximo serve de diagnóstico "
    "numérico. Note que o critério é aplicado sobre arg(1 + L), e não sobre arg L: nas altas frequências com "
    "atraso, L(jω) gira indefinidamente, mas |L| → 0 faz 1 + L ≈ 1 e não há refinamento desnecessário. "
    "O custo é O(M·n), com M avaliações de L (tipicamente 160–250) e n o grau.", recuo=False)

subsecao("Margens com fase contínua")
par("Em vez de aplicar *unwrap* à fase amostrada — frágil quando −ωτ cresce rapidamente —, a fase é calculada "
    "analiticamente como arg K + Σ arg(jω − z_i) − Σ arg(jω − p_i) − ωτ. Cada parcela é contínua em ω, de modo "
    "que a soma é contínua por construção. Os cruzamentos |L| = 1 e arg L = −180° + 360°k são detectados numa "
    "malha logarítmica de 6000 pontos e refinados por bisseção geométrica até precisão relativa de 10^−12. "
    "Também se testa ω = 0, onde L(0) < 0 é comum para P > 0.")

subsecao("Routh–Hurwitz em aritmética de ponto flutuante e exata")
par("A tabela é construída em *float* ou com frações racionais exatas (*fractions.Fraction*), o que permite "
    "medir o erro de arredondamento. Um ponto que se revelou crítico foi o teste \"elemento = 0\": numa primeira "
    "versão a tolerância era relativa ao maior coeficiente do polinômio; para n = 30, cujos coeficientes "
    "variam de 1 a 10^20, elementos legítimos eram tomados por zero, o método ε era disparado indevidamente e "
    "o veredito saía errado em todas as 8 amostras verificadas. A versão final associa a cada elemento a magnitude dos termos "
    "que o formaram, (|b₀a_(j+1)| + |a₀b_(j+1)|)/|b₀|, e só declara zero quando há cancelamento catastrófico "
    "frente a essa escala. Na aritmética exata, apenas o zero exato é zero.")

subsecao("Lugar das raízes e simulação")
par("As raízes de D + K N são obtidas pelos autovalores da matriz companheira [8]. O passo em K é dobrado quando "
    "os ramos se movem pouco e reduzido à metade quando algum ramo se desloca mais que 2% da escala do sistema; "
    "os ramos são associados entre passos por vizinho mais próximo. As regras geométricas (centroide, ângulos "
    "das assíntotas, pontos de separação por N′D − ND′ = 0 e cruzamentos do eixo jω) são calculadas à parte "
    "e servem de verificação. A resposta ao degrau usa a forma canônica controlável integrada por Runge–Kutta 4 "
    "com um *buffer* circular que implementa o atraso de forma exata.")

# ============================================================ IV. Benchmarks
secao("Plantas de Teste")
par("Os quatro cenários exigidos foram modelados conforme a Tabela II. O sistema B é um pêndulo invertido "
    "linearizado 1/(s² − 4) com compensador de avanço (s + 1)/(s + 10); o sistema C combina zero no SPD e "
    "integrador, o que exige a indentação do contorno em s = 0; o sistema D representa uma malha fechada "
    "através de uma rede com latência de 0,5 s.")
tabela("Sistemas de benchmark", ["Sist.", "L(s)", "P", "Faixa estável (Routh)"], [
    ["A", "50 / [(s+1)(s+2)(s+5)]", "0", "0 < K < 126"],
    ["B", "100(s+1) / [(s−2)(s+2)(s+10)]", "1", "K > 40"],
    ["C", "2(1−s) / [s(s+2)(s+3)]", "0", "0 < K < 5"],
    ["D", "2e^(−0,5s) / [(s+1)(0,5s+1)]", "0", "não se aplica (Padé)"],
], [0.9, 4.0, 0.6, 2.9])

# ============================================================ V. Resultados
secao("Resultados Experimentais")
subsecao("Critério de Nyquist nos quatro sistemas")
fn = figura("fig_nyquist_ABCD.png", "Diagramas de Nyquist dos sistemas A–D (linha cheia: ω > 0; tracejada: ω < 0; "
            "×: ponto crítico −1). Em B a curva envolve −1 uma vez no sentido anti-horário (N = −1), "
            "compensando o polo instável (P = 1).")
linhas = []
for k in "ABCD":
    b = B[k]
    linhas.append([k, b["P"], b["N"], b["Z"], f(b["MG"], 3) + f" ({f(b['MG_dB'], 2)} dB)",
                   f(b["MF"], 2) + "°", f(b["w_gc"], 3), f(b["margem_atraso"], 3), b["avaliacoes"]])
tabela("Resultados do critério de Nyquist e margens", ["S.", "P", "N", "Z", "MG", "MF", "ω_gc", "τ_max [s]", "aval."],
       linhas, [0.6, 0.45, 0.6, 0.45, 2.3, 1.1, 1.0, 1.2, 0.9], tam=6.5)
par(f"Todos os quatro sistemas resultaram estáveis (Z = 0), em concordância com Routh e com o cálculo direto "
    f"dos polos de malha fechada (Fig. {fn}, Tabela III). O valor não arredondado de w ficou a menos de 10^−6 do "
    "inteiro em todos os casos. Para o sistema A, MG = 2,52 coincide com 126/50 dado por Routh e "
    f"ω_pc = √17 ≈ 4,123 rad/s com a frequência de oscilação da linha auxiliar. No sistema B, MG = 0,4 (−7,96 dB) "
    "em ω = 0 é uma margem *inferior*: o ganho pode ser reduzido até 40% do valor nominal (K = 40), "
    "exatamente o limite de Routh. Cada análise exigiu menos de 300 avaliações de L(s).")
par("A suíte de testes também verifica a detecção de instabilidade: com K = 200 em A, K = 20 em B e K = 8 em C, "
    "o algoritmo obteve Z = 2, 1 e 2, iguais ao número de raízes no SPD; uma varredura de 40 valores de K em A "
    "concordou com Routh em todos os pontos.")

subsecao("Validação cruzada")
tabela("Validação cruzada com python-control", ["S.", "MG próprio", "MG control", "MF próprio [°]", "MF control [°]", "|ΔMF|"],
       [[l["sistema"], f(l["MG_proprio"], 6), f(l["MG_control"], 6), f(l["MF_proprio"], 6), f(l["MF_control"], 6),
         g(l["dif_MF"], 2)] for l in V], [0.6, 1.5, 1.5, 1.65, 1.65, 1.7], tam=6.5)
par("A Tabela IV confronta as margens com *python-control* 0.10 [5] (no sistema D, a referência usa Padé de "
    "ordem 20, pois a biblioteca não aceita atraso exato nessa função). As diferenças ficaram na casa de "
    "10^−11 graus e 10^−12 em ganho, isto é, no nível do arredondamento. Os polos de malha fechada também "
    "coincidem com os da biblioteca (tolerância 10^−8).")

subsecao("Atraso de transporte: Nyquist exato × Padé + Routh")
tabela("Sistema D: ganho e atraso críticos", ["Método", "Grau", "K_crit", "erro K", "τ_crit [s]", "erro τ"],
       [["Nyquist (exato)", "—", f(A["K_crit_exato"], 5), "—", f(A["tau_crit_exato"], 4), "—"]] +
       [[f"Padé {l['ordem']} + Routh", l["grau_polinomio"], f(l["K_crit"], 5), g(l["erro_K_%"], 2) + "%",
         f(l["tau_crit"], 4), g(l["erro_tau_%"], 2) + "%"] for l in A["pade"]],
       [1.9, 1.0, 1.3, 1.5, 1.3, 1.6], tam=6.5)
fa = figura("fig_atraso_pade.png", "Sistema D. Esquerda: Nyquist com atraso exato e com Padé de 1ª e 2ª ordens — a "
            "aproximação de 1ª ordem se afasta justamente na região próxima de −1. Direita: degrau em malha "
            "fechada simulado com atraso exato; para τ = τ_crit ≈ 1,223 s surge oscilação sustentada e, acima "
            "dele, instabilidade.")
par(f"Pelo critério de Nyquist, o atraso crítico é τ_crit = τ + MF/ω_gc = {f(A['tau_crit_exato'], 4)} s e o ganho "
    f"crítico é K·MG = {f(A['K_crit_exato'], 4)}, ambos obtidos diretamente da curva exata. Com Padé de "
    f"1ª ordem, Routh prevê K_crit = {f(pade[1]['K_crit'], 3)} ({f(pade[1]['erro_K_%'], 1)}% acima) e "
    f"τ_crit = {f(pade[1]['tau_crit'], 3)} s ({f(pade[1]['erro_tau_%'], 1)}% acima) — um erro *não "
    "conservador*, que declararia estável um sistema real instável. O erro cai rapidamente com a ordem "
    f"(Tabela V), mas cada ordem acrescenta um grau ao polinômio. A simulação no tempo (Fig. {fa}) confirma "
    "o valor de Nyquist: a resposta passa de amortecida a oscilação sustentada exatamente em τ ≈ 1,223 s.")

subsecao("Lugar das raízes e Bode")
fl = figura("fig_lugar_raizes.png", "Lugar das raízes (K normalizado) dos sistemas A, B e C, traçado com passo adaptativo. "
            "Quadrados: cruzamentos do eixo jω calculados pelas regras geométricas.")
LR = R["lugar_raizes"]
par(f"Os cruzamentos do eixo jω (Fig. {fl}) reproduzem os limites de Routh: K = 126 em ω = 4,123 rad/s para A, "
    f"K = 40 em s = 0 para B e K = 5 em ω = 1 rad/s para C. O centroide de A ({f(LR['A']['centroide'], 3)}) e o "
    f"ponto de separação ({f(LR['A']['separacao'][0], 3)}) também conferem com o cálculo manual. No sistema C, o "
    "zero no SPD atrai um ramo para o semiplano direito, efeito típico de fase não-mínima. O custo, porém, é "
    f"alto: foram necessárias {LR['A']['raizes_calculadas']} a {LR['C']['raizes_calculadas']} fatorações de "
    "polinômio por traçado, contra uma única tabela de Routh.")
fb = figura("fig_bode.png", "Diagramas de Bode de A, C e D com fase contínua. A linha pontilhada mostra a aproximação "
            "assintótica de A. A fase de D decresce sem limite por causa do termo −ωτ.", largura=Cm(6.2))
par(f"Na Fig. {fb}, as margens lidas no Bode coincidem com as de Nyquist (mesma informação, outra "
    "representação). O termo de atraso aparece como fase linear em ω, que no eixo logarítmico cai sem limite — "
    "por isso Bode também trata atraso de forma exata. O sistema B não foi incluído: com P = 1, a MG negativa "
    "(−7,96 dB) sugeriria, pela leitura direta do Bode, um sistema instável, quando a contagem de voltas "
    "mostra que ele é estável.")

subsecao("Escalabilidade e estabilidade numérica")
linhas = [[l["n"], g(l["t_routh_ms"], 2), g(l["t_raizes_eig_ms"], 2), g(l["t_nyquist_ms"], 2),
           g(l["t_bode_ms"], 2), g(l["t_lugar_raizes_ms"], 3) if l["t_lugar_raizes_ms"] else "—",
           g(l["erro_rel_routh_max"], 2), g(l["erro_rel_raizes_MA"], 2)] for l in E]
tabela("Tempo mediano [ms] e erro relativo por ordem n",
       ["n", "Routh", "Raízes", "Nyquist", "Bode", "L. raízes", "erro Routh", "erro raízes"], linhas,
       [0.75, 1.05, 1.05, 1.15, 0.95, 1.05, 1.3, 1.3], tam=6.5)
fe = figura("fig_escalabilidade.png", "Esquerda: tempo mediano por análise versus ordem. Direita: erro relativo das raízes "
            "de malha aberta (matriz companheira) e da primeira coluna de Routh em float frente à aritmética exata.")
par(f"Para cada ordem n ∈ {{5, 10, 20, 30, 40}} foram gerados de 15 a 30 sistemas aleatórios L = K/D(s), com "
    "raízes estáveis conhecidas e K escolhido de modo que parte deles ficasse instável em malha fechada. "
    "A referência de estabilidade é Routh em aritmética racional exata sobre os mesmos coeficientes. "
    f"Os resultados (Tabela VI, Fig. {fe}) mostram que:")
for item in [
    f"Routh em *float* foi o método mais rápido ({g(e40['t_routh_ms'], 2)} ms em n = 40) e manteve erro relativo "
    f"máximo de {g(e40['erro_rel_routh_max'], 2)} na primeira coluna, com 100% de acerto.",
    f"As raízes por matriz companheira têm custo O(n³) semelhante na prática, mas o erro cresce de "
    f"{g(E[0]['erro_rel_raizes_MA'], 2)} (n = 5) para {g(e40['erro_rel_raizes_MA'], 2)} (n = 40), reflexo do mau "
    "condicionamento das raízes de polinômios de grau alto. O veredito ainda acertou porque as raízes tinham "
    "folga em relação ao eixo jω.",
    f"O Nyquist adaptativo custou ~{g(e40['t_nyquist_ms'], 2)} ms em n = 40 e precisou de ~{int(e40['avaliacoes_nyquist'])} "
    "avaliações de L(s), número quase independente da ordem, e acertou 100% dos casos.",
    f"O lugar das raízes foi o mais caro ({g(e20['t_lugar_raizes_ms'], 3)} ms em n = 20), pois exige centenas "
    "de fatorações; o Durand–Kerner, alternativa sem álgebra matricial, chegou a ~1 s em n = 40.",
    "Routh exato é a referência ideal, porém de 14 a 140 vezes mais lento que o *float*, pelo crescimento dos "
    "numeradores e denominadores das frações.",
]:
    p = par(recuo=False); p.paragraph_format.left_indent = Cm(0.4)
    rich(p, "• " + item)

subsecao("Aplicação prática — trilha Ciência da Computação")
fapp = figura("fig_app.jpg", "Aplicação web interativa (HTML + JavaScript, sem dependências): polos e zeros podem ser "
              "arrastados no plano s, e ganho e atraso ajustados; Nyquist, lugar das raízes, degrau e Bode são "
              "recalculados a cada interação.")
par(f"A aplicação da Fig. {fapp} reimplementa em JavaScript os mesmos algoritmos (contorno adaptativo, margens por "
    "fase contínua, Durand–Kerner para o lugar das raízes, RK4 com atraso para o degrau) e roda inteiramente no "
    "navegador. Ela reproduz os valores da Tabela III (por exemplo, MG = 1,879 e MF = 55,13° para D) e permite "
    "mostrar, ao vivo, que aumentar τ de 0,5 s para 1,3 s faz a curva de Nyquist envolver −1 duas vezes "
    "(N = 2, Z = 2) enquanto o degrau passa a divergir.")

# ============================================================ VI. Comparação
secao("Análise Comparativa")
tabela("Comparação dos métodos (validada empiricamente)", ["Característica", "Nyquist", "Routh", "L. raízes", "Bode"], [
    ["Domínio", "frequência (polar)", "s (algébrico)", "s (geométrico)", "frequência (dB/fase)"],
    ["Estab. relativa", "MG, MF, τ_max", "não", "ζ, ω_n vs K", "MG, MF"],
    ["Atraso e^(−τs)", "exato", "Padé (erro 8,9% com ordem 1)", "Padé", "exato"],
    ["P > 0", "Z = N + P", "direto", "direto", "leitura direta enganosa"],
    ["Custo medido (n=20)", f"{g(e20['t_nyquist_ms'], 2)} ms", f"{g(e20['t_routh_ms'], 2)} ms",
     f"{g(e20['t_lugar_raizes_ms'], 3)} ms", f"{g(e20['t_bode_ms'], 2)} ms"],
    ["Risco numérico", "baixo (adaptativo)", "baixo com tolerância por escala", "raízes mal condicionadas",
     "baixo"],
    ["Vantagem", "atrasos, dados experimentais", "rapidez", "efeito de K", "projeto de compensadores"],
], [1.9, 1.68, 1.68, 1.68, 1.68], tam=6.5)
par("Os experimentos confirmam a tabela proposta no enunciado do projeto, com duas observações. Primeiro, o "
    "custo de Nyquist depende muito mais da estratégia de amostragem que da ordem do sistema: com refinamento "
    "adaptativo ele ficou na casa de 1 ms, próximo ao de Bode. Segundo, a \"robustez\" de Routh depende da "
    "implementação: o mesmo algoritmo errou as 8 amostras de ordem 30 verificadas com uma tolerância ingênua e "
    "acertou 100% com a tolerância relativa à escala de cada elemento.")
par("Em termos práticos, Routh é a melhor escolha para uma resposta rápida de estável/instável em sistemas "
    "sem atraso; o lugar das raízes, para entender o efeito de um ganho ajustável; Bode, para projetar "
    "compensadores; e Nyquist sempre que houver atraso, planta instável em malha aberta ou apenas dados de "
    "resposta em frequência medidos.")

# ============================================================ VII. Conclusão
secao("Conclusão")
par("Implementamos do zero e comparamos quatro critérios de estabilidade. O critério de Nyquist, com contorno "
    "indentado e amostragem adaptativa sobre arg(1 + L), classificou corretamente todos os casos testados — "
    "incluindo planta instável, fase não-mínima com integrador e atraso puro — e produziu margens idênticas às "
    "da biblioteca python-control até o arredondamento. O caso com atraso evidenciou a principal vantagem do "
    "método: o ganho e o atraso críticos são obtidos exatamente, ao passo que a abordagem algébrica depende de "
    "Padé e, com ordem baixa, erra de forma não conservadora.")
par("Do ponto de vista computacional, o estudo mostrou que a correção numérica depende de detalhes de "
    "implementação: tolerâncias relativas à escala, fase calculada analiticamente e refinamento adaptativo "
    "foram decisivos. Como trabalhos futuros, propõe-se estender a ferramenta a sistemas discretos "
    "(contorno no círculo unitário), a sistemas MIMO pelo critério de Nyquist generalizado e à leitura de "
    "respostas em frequência medidas experimentalmente.")

# ============================================================ contribuições e referências
p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=8, depois=4, recuo=False)
r = p.add_run("CONTRIBUIÇÃO DOS AUTORES"); r.font.size = Pt(10); r.font.small_caps = True
par(f"**{AUTORES[0]}**: implementação do critério de Nyquist (contorno, amostragem adaptativa e contagem de "
    "voltas), cálculo das margens e do atraso crítico, módulo de Padé, simulação com atraso e aplicação web "
    "interativa (trilha CC).")
par(f"**{AUTORES[1]}**: implementação da tabela de Routh–Hurwitz (casos especiais e aritmética exata), lugar "
    "das raízes, diagrama de Bode, suíte de testes unitários, validação cruzada e estudo de escalabilidade.")
par("Ambos os autores modelaram as plantas de teste, analisaram os resultados e redigiram o artigo.")

p = par(alin=WD_ALIGN_PARAGRAPH.CENTER, antes=8, depois=4, recuo=False)
r = p.add_run("REFERÊNCIAS"); r.font.size = Pt(10); r.font.small_caps = True
refs = [
    "K. Ogata, *Engenharia de Controle Moderno*, 5ª ed. São Paulo: Pearson, 2010.",
    "N. S. Nise, *Engenharia de Sistemas de Controle*, 7ª ed. Rio de Janeiro: LTC, 2017.",
    "K. J. Åström e R. M. Murray, *Feedback Systems: An Introduction for Scientists and Engineers*. "
    "Princeton, NJ: Princeton University Press, 2008.",
    "H. Nyquist, \"Regeneration theory,\" *Bell System Technical Journal*, vol. 11, no. 1, pp. 126–147, 1932.",
    "S. Fuller, B. Greiner, J. Moore, R. Murray, R. van Paassen e R. Yorke, \"The Python Control Systems Library "
    "(python-control),\" in *Proc. 60th IEEE Conf. Decision and Control (CDC)*, 2021, pp. 4875–4881.",
    "C. R. Harris *et al.*, \"Array programming with NumPy,\" *Nature*, vol. 585, pp. 357–362, 2020.",
    "G. A. Baker Jr. e P. Graves-Morris, *Padé Approximants*, 2ª ed. Cambridge: Cambridge University Press, 1996.",
    "A. Edelman e H. Murakami, \"Polynomial roots from companion matrix eigenvalues,\" *Mathematics of "
    "Computation*, vol. 64, no. 210, pp. 763–776, 1995.",
]
for i, ref in enumerate(refs, 1):
    p = par(alin=WD_ALIGN_PARAGRAPH.JUSTIFY, depois=1, recuo=False)
    p.paragraph_format.left_indent = Cm(0.6); p.paragraph_format.first_line_indent = Cm(-0.6)
    rr = p.add_run(f"[{i}]  "); rr.font.size = Pt(8)
    rich(p, ref, 8)

doc.save(SAIDA)
print("ok ->", SAIDA)
