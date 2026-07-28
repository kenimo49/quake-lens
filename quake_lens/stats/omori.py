"""修正大森則を Ogata (1983) の MLE でフィットする。

λ(t) = K / (t + c)^p     for t in [t_start, t_end]

N個の観測余震時刻に対して、(c, p) を固定すればKは閉形式のMLEを持つ:
    K* = N / integral(c, p),   integral = ∫ (t+c)^{-p} dt over [t_start, t_end]

したがって最適化は (c, p) の2次元となり、以下を最小化する:
    f(c, p) = N*log(integral(c, p)) + p*sum(log(t_i+c))
"""

from __future__ import annotations

import math
from typing import Iterable


def _integral(c: float, p: float, t_start: float, t_end: float) -> float:
    a, b = t_start + c, t_end + c
    if a <= 0 or b <= 0:
        raise ValueError("integration bounds require t+c > 0")
    if abs(p - 1.0) < 1e-9:
        return math.log(b / a)
    return (b ** (1.0 - p) - a ** (1.0 - p)) / (1.0 - p)


def loglik(K: float, c: float, p: float, times: list[float], t_start: float, t_end: float) -> float:
    """修正大森則 (非同次Poisson過程) の完全な対数尤度を返す。"""
    if K <= 0 or c <= 0 or p <= 0:
        return float("-inf")
    s = 0.0
    for t in times:
        arg = t + c
        if arg <= 0:
            return float("-inf")
        s += math.log(arg)
    integ = _integral(c, p, t_start, t_end)
    return len(times) * math.log(K) - p * s - K * integ


def _neg_profile(c: float, p: float, times: list[float], t_start: float, t_end: float) -> float:
    if c <= 0 or p <= 0:
        return float("inf")
    try:
        integ = _integral(c, p, t_start, t_end)
    except ValueError:
        return float("inf")
    if integ <= 0:
        return float("inf")
    s = 0.0
    for t in times:
        arg = t + c
        if arg <= 0:
            return float("inf")
        s += math.log(arg)
    n = len(times)
    return n * math.log(integ) + p * s


def _nelder_mead(f, x0, step=0.2, xtol=1e-7, ftol=1e-7, max_iter=800):
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        v = list(x0)
        v[i] = v[i] + step
        simplex.append(v)
    values = [f(*v) for v in simplex]
    for _ in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: values[i])
        simplex = [simplex[i] for i in order]
        values = [values[i] for i in order]
        if max(abs(values[i] - values[0]) for i in range(1, n + 1)) < ftol:
            break
        spread = 0.0
        for i in range(1, n + 1):
            for k in range(n):
                spread = max(spread, abs(simplex[i][k] - simplex[0][k]))
        if spread < xtol:
            break
        centroid = [sum(simplex[i][k] for i in range(n)) / n for k in range(n)]
        worst = simplex[-1]
        xr = [centroid[k] + (centroid[k] - worst[k]) for k in range(n)]
        fr = f(*xr)
        if values[0] <= fr < values[-2]:
            simplex[-1] = xr
            values[-1] = fr
            continue
        if fr < values[0]:
            xe = [centroid[k] + 2.0 * (centroid[k] - worst[k]) for k in range(n)]
            fe = f(*xe)
            if fe < fr:
                simplex[-1] = xe
                values[-1] = fe
            else:
                simplex[-1] = xr
                values[-1] = fr
            continue
        xc = [centroid[k] + 0.5 * (worst[k] - centroid[k]) for k in range(n)]
        fc = f(*xc)
        if fc < values[-1]:
            simplex[-1] = xc
            values[-1] = fc
            continue
        for i in range(1, n + 1):
            simplex[i] = [
                simplex[0][k] + 0.5 * (simplex[i][k] - simplex[0][k]) for k in range(n)
            ]
            values[i] = f(*simplex[i])
    return simplex[0], values[0]


def _grid_search(
    times: list[float], t_start: float, t_end: float
) -> tuple[float, float, float]:
    c_grid = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
    p_grid = [0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.6, 1.9]
    best = (0.01, 1.0, float("inf"))
    for c in c_grid:
        for p in p_grid:
            v = _neg_profile(c, p, times, t_start, t_end)
            if v < best[2]:
                best = (c, p, v)
    return best


def fit(
    times: Iterable[float],
    t_start: float | None = None,
    t_end: float | None = None,
) -> dict[str, float]:
    ts = sorted(float(t) for t in times)
    if not ts:
        raise ValueError("no aftershock times provided")
    if t_start is None:
        t_start = 0.0
    if t_end is None:
        t_end = max(ts)
    ts = [t for t in ts if t_start <= t <= t_end]
    n = len(ts)
    if n < 3:
        raise ValueError(f"need >=3 aftershocks in window; got {n}")
    if t_end <= t_start:
        raise ValueError("t_end must be > t_start")

    c0, p0, _ = _grid_search(ts, t_start, t_end)

    def objective(log_c: float, log_p: float) -> float:
        c = math.exp(log_c)
        p = math.exp(log_p)
        return _neg_profile(c, p, ts, t_start, t_end)

    (log_c_hat, log_p_hat), _ = _nelder_mead(
        objective, [math.log(c0), math.log(p0)], step=0.5
    )
    c_hat = math.exp(log_c_hat)
    p_hat = math.exp(log_p_hat)
    K_hat = n / _integral(c_hat, p_hat, t_start, t_end)
    ll = loglik(K_hat, c_hat, p_hat, ts, t_start, t_end)
    return {
        "K": K_hat,
        "c": c_hat,
        "p": p_hat,
        "logL": ll,
        "n": n,
        "t_start": t_start,
        "t_end": t_end,
    }
