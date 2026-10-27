"""Shared test setup for the agent app.

The app lazily builds ``AsyncDatabricksOpenAI()`` when a request handler runs.
These dummy values keep any SDK setup deterministic if a test exercises that
boundary; no test may make a network call with them.
"""

import os

os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")
