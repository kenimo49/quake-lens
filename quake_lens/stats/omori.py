"""修正大森則を Ogata (1983) の MLE でフィットする。

λ(t) = K / (t + c)^p     for t in [t_start, t_end]

N個の観測余震時刻に対して、(c, p) を固定すればKは閉形式のMLEを持つ:
    K* = N / integral(c, p),   integral = ∫ (t+c)^{-p} dt over [t_start, t_end]

したがって最適化は (c, p) の2次元となり、以下を最小化する:
    f(c, p) = N*log(integral(c, p)) + p*sum(log(t_i+c))

尤度関数の導出と最適化手順の詳細は docs/likelihood.md を参照。
"""

from __future__ import annotations

import math
from typing import Iterable

from quake_lens.stats._optim import _nelder_mead


def _integral(c: float, p: float, t_start: float, t_end: float) -> float:
    a, b = t_start + c, t_end + c
    if a <= 0 or b <= 0:
        raise ValueError("integration bounds require t+c > 0")
    if abs(p - 1.0) < 1e-9:
        return math.log(b / a)
    return (b ** (1.0 - p) - a ** (1.0 - p)) / (1.0 - p)


def _sum_log_shifted(times: list[float], c: float) -> float:
    """Σ log(t_i + c) を計算する。

    どれか1つでも `t_i + c <= 0` になった時点で `ValueError` を送出する。
    呼び出し側 (`loglik` / `_neg_profile`) はこれを捕捉して、それぞれの
    領域外センチネル (`-inf` / `+inf`) に変換する責務を負う。
    """
    s = 0.0
    for t in times:
        arg = t + c
        if arg <= 0:
            raise ValueError("t + c must be > 0")
        s += math.log(arg)
    return s


def loglik(K: float, c: float, p: float, times: list[float], t_start: float, t_end: float) -> float:
    """修正大森則 (非同次Poisson過程) の完全な対数尤度を返す。"""
    if K <= 0 or c <= 0 or p <= 0:
        return float("-inf")
    try:
        s = _sum_log_shifted(times, c)
    except ValueError:
        return float("-inf")
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
    try:
        s = _sum_log_shifted(times, c)
    except ValueError:
        return float("inf")
    n = len(times)
    return n * math.log(integ) + p * s


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
    """余震時刻の系列 (本震からの経過日数) に修正大森則をMLEでフィットする。

    グリッドサーチで初期値を選び、log空間のNelder-Meadで (c, p) を推定、
    K は閉形式で復元する。手順の詳細は docs/likelihood.md を参照。
    """
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
