"""HTTP fetch with bounded retries. Public files only; no API keys."""

from __future__ import annotations

import time
from typing import Protocol

import httpx

from nem_grid_pulse.settings import USER_AGENT

RETRYABLE_STATUS = {403, 408, 429, 500, 502, 503, 504}


class MissingDatasetError(RuntimeError):
    """The publisher returned 404 for one file."""


class SourceUnavailableError(RuntimeError):
    """The publisher could not be reached after retries."""


class UnexpectedStatusError(RuntimeError):
    """A non-retryable HTTP error, usually a bug in the request."""


class _Response(Protocol):
    status_code: int
    content: bytes


class _Client(Protocol):
    def get(self, url: str) -> _Response: ...


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=20.0),
    )


def fetch_bytes(
    url: str,
    client: _Client,
    *,
    attempts: int = 4,
    sleep=time.sleep,
    backoff_seconds: float = 1.0,
    max_bytes: int = 20_000_000,
) -> bytes:
    delay = backoff_seconds
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            status = response.status_code
            if status == 404:
                raise MissingDatasetError(url)
            if status in RETRYABLE_STATUS:
                raise SourceUnavailableError(f"HTTP {status} for {url}")
            if status >= 400:
                raise UnexpectedStatusError(f"HTTP {status} for {url}")
            content = response.content
            if len(content) > max_bytes:
                raise UnexpectedStatusError(f"{url} is {len(content)} bytes, over the {max_bytes} cap")
            return content
        except MissingDatasetError:
            raise
        except UnexpectedStatusError:
            raise
        except (SourceUnavailableError, httpx.TransportError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            sleep(delay)
            delay *= 2
    raise SourceUnavailableError(f"failed to fetch {url}") from last_error
