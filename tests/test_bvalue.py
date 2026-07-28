import math
import random

import pytest

from quake_lens.stats import bvalue


def _synth_exponential_mags(n, b, mc, seed):
    """Continuous exponential magnitudes above Mc with slope b."""
    rng = random.Random(seed)
    beta = b * math.log(10)
    return [mc - math.log(1.0 - rng.random()) / beta for _ in range(n)]


def test_estimate_recovers_b_from_continuous_catalog():
    mags = _synth_exponential_mags(n=5000, b=1.0, mc=2.0, seed=42)
    result = bvalue.estimate(mags, mc=2.0, delta_m=0.0)
    assert abs(result["b"] - 1.0) < 0.1
    assert result["n"] == 5000
    assert result["se"] > 0


def test_estimate_recovers_b_from_binned_catalog():
    """With rounding to ΔM=0.1, Aki correction (Mc - ΔM/2) is unbiased."""
    rng = random.Random(7)
    b = 1.0
    mc = 2.0
    dm = 0.1
    beta = b * math.log(10)
    mags = []
    while len(mags) < 8000:
        z = -math.log(1.0 - rng.random()) / beta
        m_true = (mc - dm / 2) + z
        m_reported = round(m_true / dm) * dm
        if m_reported >= mc - 1e-9:
            mags.append(round(m_reported, 2))
    result = bvalue.estimate(mags, mc=mc, delta_m=dm)
    assert abs(result["b"] - 1.0) < 0.1


def test_estimate_filters_below_mc():
    mags = [1.5, 2.0, 2.5, 3.0, 3.5]
    result = bvalue.estimate(mags, mc=2.0, delta_m=0.0)
    assert result["n"] == 4


def test_estimate_errors_on_too_few():
    with pytest.raises(ValueError):
        bvalue.estimate([1.0], mc=2.0)
