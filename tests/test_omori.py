import random

import pytest

from quake_lens.stats import omori


def _inverse_cdf(u, c, p, T):
    """Inverse CDF of density (t+c)^{-p} on [0, T] (p != 1)."""
    a = c ** (1 - p)
    b = (T + c) ** (1 - p)
    val = a + u * (b - a)
    return val ** (1.0 / (1 - p)) - c


def _synth_aftershocks(n, c, p, T, seed):
    rng = random.Random(seed)
    return sorted(_inverse_cdf(rng.random(), c, p, T) for _ in range(n))


def test_fit_recovers_p_from_synthetic():
    times = _synth_aftershocks(n=1500, c=0.01, p=1.1, T=10.0, seed=123)
    result = omori.fit(times, t_start=0.0, t_end=10.0)
    assert abs(result["p"] - 1.1) < 0.15
    assert result["n"] == 1500
    assert result["K"] > 0
    assert result["c"] > 0


def test_fit_recovers_p_at_different_value():
    times = _synth_aftershocks(n=2000, c=0.05, p=0.9, T=20.0, seed=456)
    result = omori.fit(times, t_start=0.0, t_end=20.0)
    assert abs(result["p"] - 0.9) < 0.15


def test_fit_errors_on_too_few():
    with pytest.raises(ValueError):
        omori.fit([0.1, 0.2])


def test_loglik_is_finite_for_valid_params():
    ll = omori.loglik(1.0, 0.01, 1.1, [0.1, 0.5, 2.0], 0.0, 5.0)
    assert ll > float("-inf")
