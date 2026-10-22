"""Shared test setup for the agent app.

Importing ``agent_server.agent`` builds ``AsyncDatabricksOpenAI()`` at module load,
which fails without Databricks credentials. These dummy values let the import
succeed offline; no test may make a network call with them.
"""

import os

os.environ.setdefault("DATABRICKS_HOST", "https://example.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dummy")
os.environ.setdefault("DATABRICKS_CONFIG_FILE", "/dev/null")
