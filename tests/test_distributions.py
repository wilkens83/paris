import math

from paris.engines import distributions as d


def test_poisson_pmf_sums_to_one():
    total = sum(d.poisson_pmf(k, 3.0) for k in range(0, 60))
    assert math.isclose(total, 1.0, rel_tol=1e-9)


def test_poisson_over_half_line():
    ou = d.poisson_over_under(2.5, 3.24)
    assert math.isclose(ou.p_over + ou.p_under, 1.0)
    assert ou.p_push == 0.0
    # sanity: mean 3.24 over 2.5 should be > 0.5
    assert ou.p_over > 0.5


def test_poisson_integer_line_has_push():
    ou = d.poisson_over_under(3, 3.0)
    assert ou.p_push > 0
    assert math.isclose(ou.p_over + ou.p_under + ou.p_push, 1.0, rel_tol=1e-9)


def test_negbin_reduces_to_poisson_when_not_overdispersed():
    # var <= mean -> size_from_mean_var returns None -> poisson path
    ou = d.prob_over(2.5, 3.0, variance=2.0, kind="auto")
    assert ou.distribution == "poisson"


def test_negbin_used_when_overdispersed():
    ou = d.prob_over(3.5, 4.6, variance=7.0, kind="negbin")
    assert ou.distribution == "negbin"
    assert math.isclose(ou.p_over + ou.p_under, 1.0, rel_tol=1e-6)


def test_negbin_pmf_sums_to_one():
    total = sum(d.negbin_pmf(k, 4.6, 9.0) for k in range(0, 80))
    assert math.isclose(total, 1.0, rel_tol=1e-6)


def test_normal_cdf_symmetry():
    assert math.isclose(d.normal_cdf(0, 0, 1), 0.5)
    ou = d.normal_over_under(70.5, 67.6, 12.0)
    assert ou.p_over < 0.5  # mean below the line


def test_size_from_mean_var():
    assert d.size_from_mean_var(4.0, 3.0) is None      # under-dispersed
    assert d.size_from_mean_var(4.0, 8.0) == 4.0        # 16 / 4
