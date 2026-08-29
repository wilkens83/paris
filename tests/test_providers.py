"""Provider contracts: no silent fallback, honest not-configured (directive 8, 30)."""

import pytest

from paris.config import Settings
from paris.providers import (
    ApiFootballProvider,
    ProviderNotConfigured,
    SportsGameOddsProvider,
)
from paris.providers.base import Provenance, ProviderResult


def _unconfigured_settings() -> Settings:
    return Settings(
        api_football_key=None,
        sportsgameodds_key=None,
        database_url=None,
    )


def test_api_football_not_configured_raises_with_env_var():
    p = ApiFootballProvider(settings=_unconfigured_settings())
    assert p.is_configured() is False
    with pytest.raises(ProviderNotConfigured) as exc:
        p.fixtures_today()
    assert exc.value.env_var == "API_FOOTBALL_KEY"
    assert "not configured" in str(exc.value).lower()


def test_sportsgameodds_not_configured_raises():
    p = SportsGameOddsProvider(settings=_unconfigured_settings())
    assert p.is_configured() is False
    with pytest.raises(ProviderNotConfigured) as exc:
        p.events()
    assert exc.value.env_var == "SPORTSGAMEODDS_API_KEY"


def test_provider_result_staleness():
    fresh = ProviderResult(value=[], provenance=Provenance(provider="X"))
    assert fresh.is_stale(threshold_seconds=999999) is False
    old = ProviderResult(
        value=[],
        provenance=Provenance(provider="X", source_timestamp="2000-01-01T00:00:00+00:00"),
    )
    assert old.is_stale(threshold_seconds=900) is True
