import pytest

from quake_lens.stats._optim import (
    _converged,
    _initial_simplex,
    _nelder_mead,
    _point_toward,
)


def test_initial_simplex_shape_and_vertices():
    simplex = _initial_simplex([1.0, 2.0], step=0.5)
    assert simplex == [[1.0, 2.0], [1.5, 2.0], [1.0, 2.5]]


def test_initial_simplex_does_not_mutate_x0():
    x0 = [1.0, 2.0]
    _initial_simplex(x0, step=0.5)
    assert x0 == [1.0, 2.0]


def test_point_toward_reflection():
    # 反射 (coef=1.0): 最悪点を重心の反対側へ折り返す
    assert _point_toward([0.0, 0.0], [1.0, 2.0], 1.0) == [-1.0, -2.0]


def test_point_toward_expansion():
    # 拡張 (coef=2.0): 反射方向へ2倍先まで進む
    assert _point_toward([0.0, 0.0], [1.0, 2.0], 2.0) == [-2.0, -4.0]


def test_point_toward_contraction():
    # 収縮 (coef=-0.5): 重心と最悪点の中間へ戻る
    assert _point_toward([0.0, 0.0], [1.0, 2.0], -0.5) == [0.5, 1.0]


def test_converged_by_ftol():
    simplex = [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]]
    values = [1.0, 1.0 + 1e-9, 1.0 + 1e-9]
    assert _converged(simplex, values, xtol=1e-7, ftol=1e-7)


def test_converged_by_xtol():
    simplex = [[0.0, 0.0], [1e-9, 0.0], [0.0, 1e-9]]
    values = [1.0, 2.0, 3.0]
    assert _converged(simplex, values, xtol=1e-7, ftol=1e-7)


def test_not_converged():
    simplex = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    values = [1.0, 2.0, 3.0]
    assert not _converged(simplex, values, xtol=1e-7, ftol=1e-7)


def test_minimizes_quadratic_2d():
    x, v = _nelder_mead(lambda a, b: (a - 3.0) ** 2 + (b + 1.5) ** 2, [0.0, 0.0])
    assert x[0] == pytest.approx(3.0, abs=1e-3)
    assert x[1] == pytest.approx(-1.5, abs=1e-3)
    assert v == pytest.approx(0.0, abs=1e-6)


def test_minimizes_quadratic_1d():
    x, v = _nelder_mead(lambda a: (a - 7.0) ** 4, [0.0])
    assert x[0] == pytest.approx(7.0, abs=1e-2)
    assert v == pytest.approx(0.0, abs=1e-6)


def test_minimizes_rosenbrock():
    # 谷が曲がった定番のベンチマーク。反射・拡張・収縮の経路を通る
    # (全収縮は通らないことを実測済み。全収縮は test_shrink_path でカバー)
    x, v = _nelder_mead(
        lambda a, b: (1 - a) ** 2 + 100 * (b - a * a) ** 2,
        [-1.2, 1.0],
        max_iter=5000,
    )
    assert x[0] == pytest.approx(1.0, abs=1e-3)
    assert x[1] == pytest.approx(1.0, abs=1e-3)


def test_shrink_path():
    # 階段関数は全収縮でしか前進できない: 反射点は fr=0 だが 1D では
    # values[-2] == values[0] のため採用条件 0 <= fr < 0 が偽、拡張条件
    # fr < 0 も偽、収縮点は正側で fc = 1 >= 最悪値 1 となり毎反復必ず
    # 全収縮に落ちる。全収縮が単体を縮めなければ xtol に到達できず
    # max_iter=800 まで回って評価回数が 2400 を超えるため、上限 100 の
    # assert が全収縮の動作そのものを検証する
    evals = []

    def step_fn(x):
        evals.append(x)
        return 0.0 if x <= 0 else 1.0

    x, v = _nelder_mead(step_fn, [0.0], step=0.2)
    assert x == [0.0]
    assert v == 0.0
    assert len(evals) < 100


def test_respects_max_iter():
    evals = []

    def f(a, b):
        evals.append((a, b))
        return (a - 100.0) ** 2 + (b - 100.0) ** 2

    _nelder_mead(f, [0.0, 0.0], max_iter=3)
    # 初期単体 n+1 回 + 各反復あたり高々 n+2 回 (反射1+収縮1+全収縮n) しか評価しない
    assert len(evals) <= 3 + 3 * (2 + 2)


def test_returns_best_vertex_even_without_convergence():
    x, v = _nelder_mead(
        lambda a, b: (a - 100.0) ** 2 + (b - 100.0) ** 2, [0.0, 0.0], max_iter=1
    )
    assert v == (x[0] - 100.0) ** 2 + (x[1] - 100.0) ** 2
