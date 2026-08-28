"""Data providers.

The engines never invent data (spec 64). A provider is the only thing allowed
to supply verified numbers into the pipeline. The shipped ``FileProvider`` reads
a JSON file authored by a human or an upstream research/verifier stage — it is a
deliberate boundary between "verified inputs" and "deterministic math".
"""

from .file_provider import FileProvider, load_match

__all__ = ["FileProvider", "load_match"]
