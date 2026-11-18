"""Operações básicas com polinômios, implementadas do zero.

Convenção: um polinômio é um array 1-D de coeficientes em ordem DECRESCENTE
de potência, ex.: s^2 + 3s + 2  ->  [1, 3, 2]  (mesma convenção do MATLAB).

Somente NumPy é utilizado (arrays e autovalores da matriz companheira).
"""
from __future__ import annotations

import numpy as np


def normalizar(p) -> np.ndarray:
    """Remove zeros à esquerda e devolve um array float/complex."""
    p = np.atleast_1d(np.asarray(p))
    if p.dtype.kind not in "fc":
        p = p.astype(float)
    nz = np.flatnonzero(np.abs(p) > 0)
    if nz.size == 0:
        return np.zeros(1, dtype=p.dtype)
    return p[nz[0]:]


def grau(p) -> int:
    return len(normalizar(p)) - 1


def horner(p, s):
    """Avalia p(s) pelo método de Horner. `s` pode ser escalar ou array complexo."""
    p = normalizar(p)
    s = np.asarray(s, dtype=complex)
    y = np.zeros_like(s, dtype=complex)
    for c in p:
        y = y * s + c
    return y


def somar(a, b) -> np.ndarray:
    a, b = normalizar(a), normalizar(b)
    n = max(len(a), len(b))
    a = np.concatenate([np.zeros(n - len(a)), a])
    b = np.concatenate([np.zeros(n - len(b)), b])
    return normalizar(a + b)


def multiplicar(a, b) -> np.ndarray:
    """Convolução direta dos coeficientes (produto de polinômios)."""
    a, b = normalizar(a), normalizar(b)
    out = np.zeros(len(a) + len(b) - 1, dtype=np.result_type(a, b, float))
    for i, ai in enumerate(a):
        out[i:i + len(b)] += ai * b
    return out


def escalar(a, k) -> np.ndarray:
    return normalizar(np.asarray(a, dtype=float) * k)


def derivar(p) -> np.ndarray:
    p = normalizar(p)
    n = len(p) - 1
    if n == 0:
        return np.zeros(1)
    return p[:-1] * np.arange(n, 0, -1)


def de_raizes(raizes) -> np.ndarray:
    """Monta o polinômio mônico a partir das raízes: prod (s - r_i)."""
    p = np.array([1.0 + 0j])
    for r in raizes:
        p = multiplicar(p, [1.0, -r])
    if np.allclose(p.imag, 0, atol=1e-9 * max(1.0, np.max(np.abs(p)))):
        p = p.real
    return p


def raizes(p) -> np.ndarray:
    """Raízes via autovalores da matriz companheira (Frobenius).

    Para p(s) = a0 s^n + a1 s^(n-1) + ... + an, a matriz companheira C tem
    a primeira linha -[a1..an]/a0 e subdiagonal identidade. Seus autovalores
    são exatamente as raízes de p. É o mesmo princípio usado por numpy.roots,
    mas aqui montado explicitamente.
    """
    p = normalizar(p)
    # raízes nulas (coeficientes finais zero)
    nz_fim = 0
    while len(p) > 1 and p[-1] == 0:
        p = p[:-1]
        nz_fim += 1
    n = len(p) - 1
    if n < 1:
        return np.zeros(nz_fim, dtype=complex)
    C = np.zeros((n, n), dtype=np.result_type(p, float))
    C[0, :] = -p[1:] / p[0]
    if n > 1:
        C[1:, :-1] = np.eye(n - 1)
    r = np.linalg.eigvals(C).astype(complex)
    return np.concatenate([r, np.zeros(nz_fim, dtype=complex)])


def durand_kerner(p, tol=1e-12, max_iter=500) -> np.ndarray:
    """Método iterativo de Durand–Kerner (Weierstrass), alternativa sem álgebra matricial.

    Usado no benchmark para comparar custo/precisão com a matriz companheira.
    """
    p = normalizar(p).astype(complex)
    p = p / p[0]
    n = len(p) - 1
    if n < 1:
        return np.zeros(0, dtype=complex)
    raio = 1 + np.max(np.abs(p[1:]))
    z = raio * (0.4 + 0.9j) ** np.arange(n)
    for _ in range(max_iter):
        z_old = z.copy()
        for i in range(n):
            den = np.prod(z[i] - np.delete(z, i))
            z[i] = z[i] - horner(p, z[i]) / den
        if np.max(np.abs(z - z_old)) < tol * max(1.0, np.max(np.abs(z))):
            break
    return z
