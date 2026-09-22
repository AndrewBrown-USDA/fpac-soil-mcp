"""Direct unit tests for the shared HTTP request retry helper."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from fpac_soil_mcp.http_client import (
    HttpRequestError,
    HttpStatusError,
    execute_http_request_with_retry,
)


def test_successful_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://example.com/test?param=val"
        return httpx.Response(200, json={"status": "ok"})

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    resp = execute_http_request_with_retry(
        "GET",
        "https://example.com/test",
        params={"param": "val"},
        client=mock_client,
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_retryable_status_eventual_success():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json={"success": True})

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    with patch("fpac_soil_mcp.http_client.sleep") as mock_sleep:
        resp = execute_http_request_with_retry(
            "POST",
            "https://example.com/retry",
            max_retries=3,
            backoff_factor=0.1,
            client=mock_client,
        )

    assert attempts == 3
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(0.1 * (2**0))
    mock_sleep.assert_any_call(0.1 * (2**1))


def test_retryable_status_exhaustion_raises_http_status_error():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="Internal Server Error")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    with (
        patch("fpac_soil_mcp.http_client.sleep"),
        pytest.raises(HttpStatusError) as exc_info,
    ):
        execute_http_request_with_retry(
            "GET",
            "https://example.com/fail",
            max_retries=2,
            backoff_factor=0.01,
            client=mock_client,
        )

    assert attempts == 3  # Initial + 2 retries
    assert exc_info.value.status_code == 500


def test_non_retryable_status_fails_immediately():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, text="Bad Request")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    with (
        patch("fpac_soil_mcp.http_client.sleep") as mock_sleep,
        pytest.raises(HttpStatusError) as exc_info,
    ):
        execute_http_request_with_retry(
            "GET",
            "https://example.com/bad",
            max_retries=3,
            client=mock_client,
        )

    assert attempts == 1  # 400 is not in default retry list
    assert exc_info.value.status_code == 400
    assert mock_sleep.call_count == 0


def test_empty_retry_status_codes_disables_status_retries():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="Server Error")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    with (
        patch("fpac_soil_mcp.http_client.sleep") as mock_sleep,
        pytest.raises(HttpStatusError) as exc_info,
    ):
        execute_http_request_with_retry(
            "GET",
            "https://example.com/no-retry",
            max_retries=3,
            retry_status_codes=set(),  # Explicitly empty set
            client=mock_client,
        )

    assert attempts == 1  # Should NOT retry 500 when retry_status_codes is empty
    assert exc_info.value.status_code == 500
    assert mock_sleep.call_count == 0


def test_request_error_retries_and_raises_http_request_error():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("Connection refused")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    with (
        patch("fpac_soil_mcp.http_client.sleep") as mock_sleep,
        pytest.raises(HttpRequestError, match="Connection refused"),
    ):
        execute_http_request_with_retry(
            "GET",
            "https://example.com/network-error",
            max_retries=2,
            backoff_factor=0.01,
            client=mock_client,
        )

    assert attempts == 3  # Initial + 2 retries
    assert mock_sleep.call_count == 2


def test_client_ownership_and_lifecycle():
    # 1. Injected client should NOT be closed
    mock_injected = MagicMock(spec=httpx.Client)
    mock_injected.request.return_value = httpx.Response(200, json={})
    execute_http_request_with_retry("GET", "https://example.com", client=mock_injected)
    assert not mock_injected.close.called

    # 2. Transient client (client=None) SHOULD be closed
    with patch("httpx.Client") as mock_client_cls:
        instance = MagicMock()
        instance.request.return_value = httpx.Response(200, json={})
        mock_client_cls.return_value = instance

        execute_http_request_with_retry("GET", "https://example.com", client=None)
        assert instance.close.called


def test_invalid_arguments_validation():
    with pytest.raises(ValueError, match="max_retries must be non-negative"):
        execute_http_request_with_retry("GET", "https://example.com", max_retries=-1)

    with pytest.raises(ValueError, match="backoff_factor must be non-negative"):
        execute_http_request_with_retry("GET", "https://example.com", backoff_factor=-0.5)
