# Quickstart Guide: FPAC Soil MCP Server

Get up and running with the **FPAC Soil MCP Server** in less than two minutes.

---

## 1. Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended)

---

## 2. Instant Local Run

Clone the repository and change into the project directory:

```bash
git clone https://github.com/AndrewBrown-USDA/fpac-soil-mcp.git
cd fpac-soil-mcp
```

Sync dependencies and run the server directly (stdio mode):

```bash
uv sync
uv run fpac-soil-mcp
```

---

## 3. Client Configuration

The server runs over standard I/O (`stdio`) by default and integrates with any MCP-compliant client or agent (e.g., Pi coding agent via `pi-mcp-adapter`, Claude, Cursor, Copilot CLI, or custom clients).

### Standard MCP Configuration (`.mcp.json` or client config)

Define the server in your project's `.mcp.json` or client configuration file:

```json
{
  "mcpServers": {
    "fpac-soil": {
      "command": "uv",
      "args": [
        "run",
        "fpac-soil-mcp"
      ]
    }
  }
}
```

*Note: If your client runs from a different working directory, add the project path via `--directory /path/to/fpac-soil-mcp` before `run`.*

---

## 4. Try These Prompts in Your LLM

Once connected, test the server tools, resources, and prompt templates using these sample queries:

### Discovery & Capabilities
> *"What tools, resources, and prompt templates do you have available for FPAC-NRCS soil data and FPPA screening?"*

### Point Screening Query (`get_farmland_classification_by_point`)
- **Urban / Non-Prime Farmland:**
  > *"Can you check the soil map unit and farmland classification for latitude `39.7684` and longitude `-86.1581`?"*
- **Conditional Prime Farmland:**
  > *"Can you check the soil map unit and farmland classification for latitude `39.7684` and longitude `-87.1581`?"*
- **Prime Farmland / General Point:**
  > *"What is the USDA soil map unit and farmland classification at latitude `41.8781`, longitude `-93.0977`?"*

### Map Unit Key (mukey) Query (`get_farmland_classification_by_mukey`)
- **Direct Map Unit Lookup:**
  > *"Retrieve the farmland classification and soil map unit details for SSURGO map unit key (mukey) `3104713`."*
- **Conditional Prime Map Unit:**
  > *"Retrieve the farmland classification and soil map unit details for SSURGO map unit key (mukey) `159756`."*

### FPPA Scope & Regulatory Boundaries (`explain_fppa_screening_scope`)
> *"Explain the difference between preliminary SDA soil screening and a full FPPA LESA determination or Form AD-1006."*

### Farmland Classification Definitions (`list_farmland_classes`)
> *"List all official USDA NRCS farmland classification categories and their FPPA significance."*

### FPPA Screening Assistant Prompt (`fppa_screening_assistant`)
> *"Use the `fppa_screening_assistant` prompt to evaluate a proposed highway extension project at `39.7684, -87.1581`."*

### Validation & Out-of-Bounds Edge Cases
- **Invalid Latitude:**
  > *"Can you check the soil map unit and farmland classification for latitude `120.0` and longitude `-87.1581`?"*
- **Unmapped / Geographic Boundary (Arctic Ocean):**
  > *"Can you check the soil map unit and farmland classification for latitude `89.0` and longitude `-87.1581`?"*
- **Invalid Map Unit Key:**
  > *"Retrieve the farmland classification and soil map unit details for SSURGO map unit key (mukey) `asdgasdg`."*

---

## 5. Development & Testing

```bash
# Run unit tests
uv run pytest

# Check code quality
uv run ruff check .
```
