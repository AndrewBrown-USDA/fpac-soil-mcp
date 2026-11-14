"""Shared HTTP request helpers for external integrations."""

from collections.abc import Mapping
from time import sleep
from typing import Any

import httpx

from fpac_soil_mcp.core.errors import UpstreamError


class HttpClientError(UpstreamError):
    """Base exception for normalized HTTP client failures."""


class HttpRequestError(HttpClientError):
    """Raised when an HTTP request cannot be completed."""


class HttpStatusError(HttpClientError):
    """Raised when a response has an unsuccessful status code."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        self.url = str(response.request.url) if response.request else str(response.url)
        super().__init__(f"HTTP {self.status_code} for {self.url}")


def execute_http_request_with_retry(
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    data: Any = None,
    json: Any = None,
    headers: Mapping[str, str] | None = None,
    timeout: float | httpx.Timeout | None = None,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    retry_status_codes: set[int] | frozenset[int] | None = None,
    client: httpx.Client | None = None,
) -> httpx.Response:
    """Execute an HTTP request, retrying configured transient failures."""
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    if backoff_factor < 0:
        raise ValueError("backoff_factor must be non-negative")

    retryable = (
        retry_status_codes
        if retry_status_codes is not None
        else frozenset({429, 500, 502, 503, 504})
    )
    owns_client = client is None
    http_client = client or httpx.Client(timeout=timeout)
    try:
        for attempt in range(max_retries + 1):
            try:
                response = http_client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                )
            except httpx.RequestError as exc:
                if attempt >= max_retries:
                    raise HttpRequestError(f"HTTP request failed for {url}: {exc}") from exc
                sleep(backoff_factor * (2**attempt))
                continue

            if response.status_code in retryable and attempt < max_retries:
                sleep(backoff_factor * (2**attempt))
                continue
            if response.is_error:
                raise HttpStatusError(response)
            return response
    finally:
        if owns_client:
            http_client.close()

    raise HttpRequestError(f"HTTP request failed for {url}")
