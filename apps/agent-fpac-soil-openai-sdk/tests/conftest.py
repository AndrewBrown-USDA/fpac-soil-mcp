"""Shared test setup for the agent app.

The app lazily builds ``AsyncDatabricksOpenAI()`` when a request handler runs.
These dummy values keep any SDK setup deterministic if a test exercises that
boundary; no test may make a network call with them.
"""

import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")


@pytest.fixture
def valid_site_assessment_criteria_resource():
    payload = {
        "schema_version": "1.0",
        "criteria": [
            {
                "criterion_number": number,
                "question": f"Question {number}?",
                "citation": f"7 CFR § 658.5(b)({number})",
                "bands": [{"label": "Unknown or unavailable", "points": None}],
            }
            for number in range(1, 13)
        ],
    }
    return SimpleNamespace(contents=[SimpleNamespace(text=json.dumps(payload))])
