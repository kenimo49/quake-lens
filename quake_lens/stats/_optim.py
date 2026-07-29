"""汎用オプティマイザ。特定モデルの知識を持たない純粋な数値最適化ルーチン。"""

from __future__ import annotations

from typing import Callable, Sequence


def _nelder_mead(
    f: Callable[..., float],
    x0: Sequence[float],
    step: float = 0.2,
    xtol: float = 1e-7,
    ftol: float = 1e-7,
    max_iter: int = 800,
) -> tuple[list[float], float]:
    """Nelder-Mead単体法で `f(*x)` を最小化する汎用ルーチン。

    初期点 `x0` から辺長 `step` の初期単体を作り、反射・拡張・収縮・全収縮の
    標準操作を最大 `max_iter` 反復する。値のばらつきが `ftol` 未満、または
    単体の各座標のばらつきが `xtol` 未満になった時点で終了し、最良点の座標と
    その関数値を返す。omori.pyなど呼び出し側の対象関数はスカラー引数を
    複数取る形式 (`f(x1, x2, ...)`) で渡すこと。
    """
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
