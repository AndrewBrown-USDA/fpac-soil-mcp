"""Tests that the deployment files declare the FPAC agent's env vars and resources."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

APP_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "agent-fpac-soil-openai-sdk"
MCP_URL = "https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com/mcp"
MODEL = "models.ai.gpt-5-6-luna"


def _load(name: str) -> dict:
    return YAML(typ="safe").load((APP_DIR / name).read_text(encoding="utf-8"))


def _env_by_name(entries: list[dict]) -> dict[str, dict]:
    return {entry["name"]: entry for entry in entries}


@pytest.fixture(scope="module")
def app_yaml() -> dict:
    return _load("app.yaml")


@pytest.fixture(scope="module")
def bundle_app() -> dict:
    return _load("databricks.yml")["resources"]["apps"]["agent_openai_agents_sdk"]


def test_app_yaml_env(app_yaml):
    env = _env_by_name(app_yaml["env"])
    assert env["AGENT_MODEL"]["valueFrom"] == "llm-endpoint"
    assert env["FPAC_MCP_URL"]["value"] == MCP_URL
    assert env["FPAC_MCP_TIMEOUT_SECONDS"]["value"] == "180"


def test_bundle_env(bundle_app):
    env = _env_by_name(bundle_app["config"]["env"])
    assert env["AGENT_MODEL"]["value_from"] == "llm-endpoint"
    assert env["FPAC_MCP_URL"]["value"] == MCP_URL
    assert env["FPAC_MCP_TIMEOUT_SECONDS"]["value"] == "180"


def test_bundle_resources(bundle_app):
    resources = {resource["name"]: resource for resource in bundle_app["resources"]}
    assert resources["llm-endpoint"]["uc_securable"] == {
        "securable_full_name": MODEL,
        "permission": "EXECUTE",
    }
    assert resources["mcp_server"]["app"] == {"name": "mcp-fpac-soil", "permission": "CAN_USE"}


def test_bundle_app_name():
    bundle = _load("databricks.yml")
    assert bundle["resources"]["apps"]["agent_openai_agents_sdk"]["name"] == APP_NAME
    prod = bundle["targets"]["prod"]["resources"]["apps"]["agent_openai_agents_sdk"]
    assert prod["name"] == APP_NAME


def test_lockfile_uses_public_pypi():
    # The Databricks workspace package proxy is unreachable from GitHub Actions; re-lock
    # with the pyproject's PyPI default index if this fails.
    assert "package-proxy" not in (APP_DIR / "uv.lock").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["app.yaml", "databricks.yml", ".env.example"])
def test_disabled_model_not_referenced(name):
    # databricks-claude-sonnet-5-5 is disabled in this workspace (403 PERMISSION_DENIED).
    assert "databricks-claude-sonnet-5-5" not in (APP_DIR / name).read_text(encoding="utf-8")
