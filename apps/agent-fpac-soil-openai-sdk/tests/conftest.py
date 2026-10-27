"""Shared test setup for the agent app.

Importing ``agent_server.agent`` builds ``AsyncDatabricksOpenAI()`` at module load,
which requires Databricks environment variables. These dummy values let the import
proceed without real credentials; no test may make a network call with them.
"""

import os

os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")
