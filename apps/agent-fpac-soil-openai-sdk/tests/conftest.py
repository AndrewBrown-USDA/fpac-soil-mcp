"""Shared test setup for the agent app.

The app lazily builds ``AsyncDatabricksOpenAI()`` when a request handler runs.
These dummy values keep any SDK setup deterministic if a test exercises that
boundary; no test may make a network call with them.
"""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")


@pytest.fixture
def valid_site_assessment_criteria_resource():
    registry_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "fpac_soil_mcp"
        / "data"
        / "site_assessment.v1.json"
    )
    return SimpleNamespace(
        contents=[SimpleNamespace(text=registry_path.read_text(encoding="utf-8"))]
    )
