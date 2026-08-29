"""Small proxy-aware HTTP client with retries (directive 8).

Dependency-free (stdlib ``urllib``). Honors the environment's proxy settings so
it works behind the agent proxy. Retries transient failures with exponential
backoff; a persistent failure raises ``ProviderUnavailable`` — never a fake
response.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

from .base import ProviderUnavailable


def get_json(
    url: str,
    *,
    provider: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
    max_retries: int = 3,
    backoff_base: float = 1.5,
) -> Any:
    """GET ``url`` and parse JSON, retrying transient errors.

    Raises ProviderUnavailable after the retry budget is exhausted.
    """
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{query}" if query else url

    last_detail = ""
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            # urllib picks up HTTP(S)_PROXY from the environment automatically
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            # 4xx (except 429) are not retryable
            if exc.code != 429 and 400 <= exc.code < 500:
                detail = f"HTTP {exc.code} {exc.reason}"
                try:
                    detail += f": {exc.read().decode('utf-8')[:200]}"
                except Exception:
                    pass
                raise ProviderUnavailable(provider, detail) from exc
            last_detail = f"HTTP {exc.code} {exc.reason}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_detail = str(exc)

        if attempt < max_retries:
            time.sleep(backoff_base ** attempt)

    raise ProviderUnavailable(provider, f"failed after {max_retries} attempts: {last_detail}")
