"""汎用オプティマイザ。特定モデルの知識を持たない純粋な数値最適化ルーチン。

アルゴリズムの各操作（反射・拡張・収縮・全収縮）の意味は
docs/likelihood.md の最適化手順の節を参照。
"""

from __future__ import annotations

from typing import Callable, Sequence


def _initial_simplex(x0: Sequence[float], step: float) -> list[list[float]]:
    """初期点の各座標を step ずつ動かして n+1 頂点の初期単体を作る。"""
    simplex = [list(x0)]
    for i in range(len(x0)):
        v = list(x0)
        v[i] = v[i] + step
        simplex.append(v)
    return simplex


def _converged(
    simplex: list[list[float]],
    values: list[float],
    xtol: float,
    ftol: float,
) -> bool:
    """単体が十分に縮んだかを判定する。

    最良点に対する関数値のばらつきが `ftol` 未満、または各座標のばらつきが
    `xtol` 未満なら収束とみなす。単体はソート済み（先頭が最良）を前提とする。
    """
    n = len(simplex) - 1
    if max(abs(values[i] - values[0]) for i in range(1, n + 1)) < ftol:
        return True
    spread = max(
        abs(simplex[i][k] - simplex[0][k]) for i in range(1, n + 1) for k in range(n)
    )
    return spread < xtol


def _point_toward(
    centroid: list[float], worst: list[float], coef: float
) -> list[float]:
    """重心から最悪点と反対方向へ coef 倍動かした点を返す。

    coef の値が Nelder-Mead の操作に対応する: 反射 = 1.0、拡張 = 2.0、
    収縮 = −0.5（負の係数は最悪点側へ戻ることを意味する）。
    """
    return [centroid[k] + coef * (centroid[k] - worst[k]) for k in range(len(centroid))]


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
    標準操作を最大 `max_iter` 反復する。収束判定は `_converged` を参照。
    最良点の座標とその関数値を返す。omori.pyなど呼び出し側の対象関数は
    スカラー引数を複数取る形式 (`f(x1, x2, ...)`) で渡すこと。
    """
    n = len(x0)
    simplex = _initial_simplex(x0, step)
    values = [f(*v) for v in simplex]
    for _ in range(max_iter):
        # 良い順に並べ替える。以降 simplex[0] が最良、simplex[-1] が最悪
        order = sorted(range(n + 1), key=lambda i: values[i])
        simplex = [simplex[i] for i in order]
        values = [values[i] for i in order]
        if _converged(simplex, values, xtol, ftol):
            break
        # 最悪点を除く n 頂点の重心。移動は常にこの重心を基準に行う
        centroid = [sum(simplex[i][k] for i in range(n)) / n for k in range(n)]
        worst = simplex[-1]

        # 反射: 最悪点を重心の反対側へ折り返す
        xr = _point_toward(centroid, worst, 1.0)
        fr = f(*xr)
        if values[0] <= fr < values[-2]:
            # 最良ではないが2番目の最悪よりは良い → 反射点をそのまま採用
            simplex[-1] = xr
            values[-1] = fr
            continue
        if fr < values[0]:
            # 反射点が最良を更新 → その方向が有望なので2倍先まで拡張を試す
            xe = _point_toward(centroid, worst, 2.0)
            fe = f(*xe)
            if fe < fr:
                simplex[-1] = xe
                values[-1] = fe
            else:
                simplex[-1] = xr
                values[-1] = fr
            continue
        # 反射が失敗 → 収縮: 重心と最悪点の中間まで戻って試す
        xc = _point_toward(centroid, worst, -0.5)
        fc = f(*xc)
        if fc < values[-1]:
            simplex[-1] = xc
            values[-1] = fc
            continue
        # 収縮も失敗 → 全収縮: 最良点へ向けて単体全体を半分に縮める
        for i in range(1, n + 1):
            simplex[i] = [
                simplex[0][k] + 0.5 * (simplex[i][k] - simplex[0][k]) for k in range(n)
            ]
            values[i] = f(*simplex[i])
    return simplex[0], values[0]
