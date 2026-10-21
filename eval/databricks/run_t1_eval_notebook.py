# Databricks notebook source
# MAGIC %md
# MAGIC # T1 evaluation: ground-truth rows on serverless
# MAGIC
# MAGIC Runs the in-process MCP agent and MLflow scorers over the verified rows of
# MAGIC `eval/prompt_test_cases.json`. Results are screening-quality findings, not
# MAGIC official FPPA determinations. See `eval/databricks/README.md`.

# COMMAND ----------

# MAGIC %pip install -q -e ../.. "databricks-sdk[openai]>=0.122"

# COMMAND ----------

# MAGIC %pip install -q --force-reinstall --no-deps shapely==2.2.0

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

from run_mlflow_eval import run

ARGS = ["--ground-truth"]  # e.g. ["--cases", "POINT-01"] or ["--all"]
result = run(ARGS)
print("\n=== T1 Run Complete ===")
print(f"Run ID: {result.get('run_id', 'N/A')}")
print(f"Experiment: {result.get('experiment', 'N/A')}")
for name, counts in result.get("summary", {}).items():
    print(f"  {name}: pass={counts['pass']} fail={counts['fail']} null={counts['null']}")
