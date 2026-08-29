"""Independent verification layer (directive 22, spec 4.13).

Checks critical fields before an analysis is trusted: entity identity, data
sufficiency, market freshness, source presence. An unresolved critical conflict
forces WAIT / NO BET rather than a guessed value.
"""

from .verifier import VerificationReport, verify_prop

__all__ = ["VerificationReport", "verify_prop"]
