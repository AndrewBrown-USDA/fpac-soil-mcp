"""Offline tests for the authenticated T2 smoke runner."""

from __future__ import annotations

from types import SimpleNamespace

import httpx2
import pytest
import run_t2_smoke as smoke


def test_resolve_endpoint_looks_up_app_and_adds_mcp_path() -> None:
    calls: list[dict[str, str]] = []
    workspace = SimpleNamespace(
        apps=SimpleNamespace(
            get=lambda **kwargs: (
                calls.append(kwargs) or SimpleNamespace(url="https://soil.example/")
            )
        )
    )

    assert smoke._resolve_endpoint(workspace) == "https://soil.example/mcp"
    assert calls == [{"name": "mcp-fpac-soil"}]


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("http://soil.example", "valid HTTPS URL"),
        ("not-a-url", "valid HTTPS URL"),
        (None, "valid HTTPS URL"),
    ],
)
def test_resolve_endpoint_rejects_invalid_or_unavailable_urls(
    url: str | None, message: str
) -> None:
    workspace = SimpleNamespace(apps=SimpleNamespace(get=lambda **kwargs: SimpleNamespace(url=url)))

    with pytest.raises(smoke.SmokeError, match=message):
        smoke._resolve_endpoint(workspace)


@pytest.mark.asyncio
async def test_auth_adapter_uses_fresh_sdk_headers_without_logging_values() -> None:
    class Config:
        def authenticate(self) -> dict[str, str]:
            return {"Authorization": "Bearer test-secret"}

    auth = smoke._run_as_auth(Config())
    assert isinstance(auth, httpx2.Auth)
    request = httpx2.Request("GET", "https://soil.example/mcp")
    sent = [value async for value in auth.async_auth_flow(request)]
    assert sent[0].headers["Authorization"] == "Bearer test-secret"


@pytest.mark.asyncio
async def test_auth_adapter_sanitizes_sdk_authentication_errors() -> None:
    class Config:
        def authenticate(self) -> dict[str, str]:
            raise RuntimeError("Bearer super-secret-value")

    auth = smoke._run_as_auth(Config())
    request = httpx2.Request("GET", "https://soil.example/mcp")
    with pytest.raises(smoke.SmokeError, match="authentication failed") as exc_info:
        async for _ in auth.async_auth_flow(request):
            pass
    assert "super-secret-value" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_smoke_initializes_discovers_and_calls_in_one_client_session() -> None:
    events: list[str] = []

    class FakeClient:
        async def __aenter__(self):
            events.append("initialize")
            return self

        async def __aexit__(self, *_args):
            events.append("close")

        async def list_tools(self):
            events.append("list_tools")
            return [SimpleNamespace(name="explain_fppa_screening_scope")]

        async def call_tool(self, name: str, arguments: dict[str, object]):
            events.append(f"call:{name}")
            assert arguments == {}
            return SimpleNamespace(isError=False, content=[SimpleNamespace(text="ok")])

    def factory(endpoint: str, *, auth: object) -> FakeClient:
        assert endpoint == "https://soil.example/mcp"
        assert auth == "sdk-auth"
        events.append("construct")
        return FakeClient()

    await smoke._smoke("https://soil.example/mcp", "sdk-auth", factory)
    assert events == [
        "construct",
        "initialize",
        "list_tools",
        "call:explain_fppa_screening_scope",
        "close",
    ]


@pytest.mark.asyncio
async def test_run_async_returns_only_sanitized_success_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def successful_smoke(endpoint: str, auth: object, client_factory: object) -> None:
        assert endpoint == "https://soil.example/mcp"
        assert auth == "sdk-auth"

    monkeypatch.setattr(smoke, "_run_as_auth", lambda config: "sdk-auth")
    monkeypatch.setattr(smoke, "_smoke", successful_smoke)
    monkeypatch.setattr(smoke, "_git_sha", lambda: "abc123")
    workspace = SimpleNamespace(
        apps=SimpleNamespace(get=lambda **kwargs: SimpleNamespace(url="https://soil.example")),
        config=object(),
    )
    result = await smoke.run_async(workspace_client=workspace, client_factory=object())

    assert result == {
        "timestamp": result["timestamp"],
        "commit_sha": "abc123",
        "endpoint_host": "soil.example",
        "principal_label": "databricks-run-as",
        "auth_mode": "databricks-sdk-run-as",
        "session_mode": "stateful-streamable-http",
        "tool_name": "explain_fppa_screening_scope",
        "status": "success",
    }
    assert "test-secret" not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tools", "result", "message"),
    [
        ([], SimpleNamespace(content=["ok"]), "did not expose"),
        (
            [SimpleNamespace(name="explain_fppa_screening_scope")],
            SimpleNamespace(isError=True, content=["sensitive raw output"]),
            "invalid result",
        ),
        (
            [SimpleNamespace(name="explain_fppa_screening_scope")],
            SimpleNamespace(content=[]),
            "invalid result",
        ),
    ],
)
async def test_smoke_fails_on_missing_tool_or_invalid_result(
    tools: list[object], result: object, message: str
) -> None:
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            return tools

        async def call_tool(self, *_args):
            return result

    with pytest.raises(smoke.SmokeError, match=message) as exc_info:
        await smoke._smoke("https://soil.example/mcp", None, lambda *_args, **_kwargs: FakeClient())
    assert "sensitive raw output" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_smoke_sanitizes_transport_and_auth_failures() -> None:
    class BrokenClient:
        async def __aenter__(self):
            raise RuntimeError("Bearer super-secret-value")

        async def __aexit__(self, *_args):
            return None

    with pytest.raises(smoke.SmokeError, match="initialization") as exc_info:
        await smoke._smoke(
            "https://soil.example/mcp",
            None,
            lambda *_args, **_kwargs: BrokenClient(),
        )
    assert "super-secret-value" not in str(exc_info.value)


async def test_main_async_runs_inside_an_existing_event_loop(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def successful_run(argv: object) -> dict[str, str]:
        return {"status": "success"}

    monkeypatch.setattr(smoke, "run", successful_run)

    assert await smoke.main_async([]) == 0
    assert '"status": "success"' in capsys.readouterr().out


async def test_main_async_reports_only_the_sanitized_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def failing_run(argv: object) -> dict[str, str]:
        raise smoke.SmokeError("MCP initialization, discovery, or tool invocation failed.")

    monkeypatch.setattr(smoke, "run", failing_run)

    assert await smoke.main_async([]) == 1
    assert "T2 smoke failed: MCP initialization" in capsys.readouterr().err


def test_main_runs_without_an_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    async def successful_run(argv: object) -> dict[str, str]:
        return {"status": "success"}

    monkeypatch.setattr(smoke, "run", successful_run)

    assert smoke.main([]) == 0
