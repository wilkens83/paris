"""Provider contracts: provenance envelope + no-silent-fallback rules.

Directive 6, 8, 28, 30, 32. A provider is the ONLY thing allowed to bring real
data into the system, and every value it returns is traceable (provider, source
id, timestamps, verification status). Providers never substitute demo data — on
failure they raise a typed error the caller must handle (surface it, retry, or
mark the source unavailable), never a fabricated value.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Typed failures — no provider ever returns fake data instead of raising
# --------------------------------------------------------------------------- #
class ProviderError(Exception):
    """Base class for all provider failures."""


class ProviderNotConfigured(ProviderError):
    """A required credential/setting is missing (directive 30).

    Carries the exact env var name so the UI/API can show the precise fix.
    """

    def __init__(self, env_var: str, provider: str):
        self.env_var = env_var
        self.provider = provider
        super().__init__(
            f"{env_var} is not configured. {provider} real data cannot be loaded. "
            f"Set {env_var} in the environment (see .env.example)."
        )


class ProviderUnavailable(ProviderError):
    """The provider is configured but the request failed after retries."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider} unavailable: {detail}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Provenance:
    """Where a value came from (directive 28)."""

    provider: str
    endpoint: str = ""
    raw_external_id: str | None = None
    retrieved_at: str = field(default_factory=lambda: _now().isoformat(timespec="seconds"))
    source_timestamp: str | None = None
    verification_status: str = "UNVERIFIED"  # UNVERIFIED / VERIFIED / CONFLICT


@dataclass
class ProviderResult(Generic[T]):
    """A real value plus its provenance. ``ok`` is always True here — a failure
    is an exception, not a result, so a caller can never mistake missing data
    for a real zero (directive 25, 26)."""

    value: T
    provenance: Provenance
    ok: bool = True

    def age_seconds(self) -> float | None:
        ts = self.provenance.source_timestamp or self.provenance.retrieved_at
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (_now() - dt).total_seconds()
        except (ValueError, TypeError):
            return None

    def is_stale(self, threshold_seconds: int) -> bool:
        age = self.age_seconds()
        return age is not None and age > threshold_seconds


class DataProvider(abc.ABC):
    """Base class for every real provider."""

    name: str = "provider"

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """True when all required credentials/settings are present."""

    def require_configured(self) -> None:
        if not self.is_configured():
            raise ProviderNotConfigured(self.required_env_var(), self.name)

    @abc.abstractmethod
    def required_env_var(self) -> str:
        """The env var that must be set for this provider to function."""
