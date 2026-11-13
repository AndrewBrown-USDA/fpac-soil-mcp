# Databricks notebook source
# MAGIC %md
# MAGIC # T2 deployed MCP access smoke
# MAGIC
# MAGIC Runs the authenticated smoke check against the deployed `mcp-fpac-soil`
# MAGIC `/mcp` endpoint. Configure the Databricks job/notebook to run as the
# MAGIC dedicated T2 evaluation service principal before running this notebook.
# MAGIC The service principal must already have `CAN_USE` on the app. No PAT or
# MAGIC secret is configured by this notebook.
# MAGIC
# MAGIC The output is sanitized metadata only; this smoke does not run T1/T2
# MAGIC evaluations or query USDA/Census services. See `eval/databricks/README.md`.

# COMMAND ----------

# MAGIC %pip install -q -e ../.. "databricks-sdk>=0.122"

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821 -- Databricks notebook global

# COMMAND ----------

import os
import sys

# The notebook runs with cwd = eval/databricks/; put it and eval/ on sys.path.
here = os.getcwd()
for path in (os.path.dirname(here), here):
    if path not in sys.path:
        sys.path.insert(0, path)

from run_t2_smoke import main

exit_code = main([])
if exit_code:
    raise RuntimeError("The authenticated T2 smoke failed; see the sanitized error above.")
