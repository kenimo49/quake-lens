"""Gutenberg-Richter b-value estimator (Aki 1965 MLE)."""

from __future__ import annotations

import math
from typing import Iterable

DELTA_M = 0.1


def estimate(mags: Iterable[float], mc: float, delta_m: float = DELTA_M) -> dict[str, float]:
    """Aki MLE for b-value given magnitude completeness `mc`.

    b = log10(e) / (mean(M) - (Mc - ΔM/2))
    SE(b) = b / sqrt(N)   (Aki 1965 approximation)
    """
    used = [m for m in mags if m >= mc]
    n = len(used)
    if n < 2:
        raise ValueError(f"need >=2 events with M>=mc; got {n}")
    mean_m = sum(used) / n
    denom = mean_m - (mc - delta_m / 2.0)
    if denom <= 0:
        raise ValueError(
            f"mean(M)={mean_m:.3f} not greater than (mc-Δm/2)={mc - delta_m / 2:.3f}"
        )
    b = math.log10(math.e) / denom
    se = b / math.sqrt(n)
    return {"b": b, "se": se, "n": n, "mc": mc, "mean_m": mean_m, "delta_m": delta_m}
