"""Distribution Engine — turn a projection into P(Over) / P(Under).

Implements sections 21-24 of the master spec. The rule is explicit: never
default blindly to a normal law. Pick the distribution from the market:

    - low counts (shots, SOT, tackles ...)  -> Poisson
    - over-dispersed counts                 -> Negative Binomial
    - quasi-continuous stats                 -> Normal / Student-t

For a line with a possible push (an integer line) win / push / loss are
modelled separately (spec 23).

Everything is pure Python stdlib math so it stays portable and testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Probability mass / cumulative helpers
# --------------------------------------------------------------------------- #
def poisson_pmf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) if lam > 0 else (1.0 if k == 0 else 0.0)


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k)."""
    if k < 0:
        return 0.0
    return sum(poisson_pmf(i, lam) for i in range(0, k + 1))


def negbin_pmf(k: int, mean: float, size: float) -> float:
    """Negative Binomial pmf parameterised by mean and dispersion ``size`` (r).

    Variance = mean + mean^2 / size.  As size -> inf this tends to Poisson.
    """
    if k < 0 or mean <= 0 or size <= 0:
        return 0.0
    p = size / (size + mean)
    return math.exp(
        math.lgamma(k + size)
        - math.lgamma(size)
        - math.lgamma(k + 1)
        + size * math.log(p)
        + k * math.log(1.0 - p)
    )


def negbin_cdf(k: int, mean: float, size: float) -> float:
    if k < 0:
        return 0.0
    return sum(negbin_pmf(i, mean, size) for i in range(0, k + 1))


def size_from_mean_var(mean: float, var: float) -> float | None:
    """Solve the NB dispersion from an observed mean and variance.

    Returns None when the data is not over-dispersed (var <= mean), in which
    case Poisson is the appropriate law.
    """
    if var <= mean:
        return None
    return (mean * mean) / (var - mean)


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


# --------------------------------------------------------------------------- #
# Over/Under probability
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OverUnder:
    """Result of scoring a line against a distribution."""

    p_over: float
    p_under: float
    p_push: float = 0.0
    distribution: str = ""

    def normalized_over(self) -> float:
        """P(Over) with the push removed (money-back-on-push convention)."""
        denom = self.p_over + self.p_under
        return self.p_over / denom if denom > 0 else self.p_over


def _is_half_line(line: float) -> bool:
    return abs(line - round(line)) > 1e-9


def poisson_over_under(line: float, lam: float) -> OverUnder:
    """P(Over)/P(Under) for a count line under a Poisson(lam) law."""
    if _is_half_line(line):
        floor = math.floor(line)
        p_under = poisson_cdf(floor, lam)          # X <= floor  => under
        return OverUnder(p_over=1.0 - p_under, p_under=p_under, distribution="poisson")
    # integer line: push possible
    L = int(round(line))
    p_push = poisson_pmf(L, lam)
    p_under = poisson_cdf(L - 1, lam)
    p_over = 1.0 - p_under - p_push
    return OverUnder(p_over=p_over, p_under=p_under, p_push=p_push, distribution="poisson")


def negbin_over_under(line: float, mean: float, size: float) -> OverUnder:
    if _is_half_line(line):
        floor = math.floor(line)
        p_under = negbin_cdf(floor, mean, size)
        return OverUnder(p_over=1.0 - p_under, p_under=p_under, distribution="negbin")
    L = int(round(line))
    p_push = negbin_pmf(L, mean, size)
    p_under = negbin_cdf(L - 1, mean, size)
    p_over = 1.0 - p_under - p_push
    return OverUnder(p_over=p_over, p_under=p_under, p_push=p_push, distribution="negbin")


def normal_over_under(line: float, mu: float, sigma: float) -> OverUnder:
    p_under = normal_cdf(line, mu, sigma)
    return OverUnder(p_over=1.0 - p_under, p_under=p_under, distribution="normal")


def prob_over(
    line: float,
    mean: float,
    *,
    variance: float | None = None,
    kind: str = "auto",
    sigma: float | None = None,
) -> OverUnder:
    """Dispatch to the right distribution and return the Over/Under result.

    kind:
        "poisson"  -> discrete counts, equidispersed
        "negbin"   -> discrete counts, over-dispersed (needs variance)
        "normal"   -> quasi-continuous (needs variance or sigma)
        "auto"     -> counts: negbin if over-dispersed else poisson
    """
    kind = kind.lower()
    if kind == "poisson":
        return poisson_over_under(line, mean)
    if kind == "normal":
        s = sigma if sigma is not None else (math.sqrt(variance) if variance else 0.0)
        return normal_over_under(line, mean, s)
    if kind == "negbin":
        if variance is None:
            raise ValueError("negbin requires a variance")
        size = size_from_mean_var(mean, variance)
        if size is None:  # not over-dispersed -> Poisson is correct
            return poisson_over_under(line, mean)
        return negbin_over_under(line, mean, size)
    if kind == "auto":
        if variance is None:
            return poisson_over_under(line, mean)
        size = size_from_mean_var(mean, variance)
        if size is None:
            return poisson_over_under(line, mean)
        return negbin_over_under(line, mean, size)
    raise ValueError(f"Unknown distribution kind: {kind}")
