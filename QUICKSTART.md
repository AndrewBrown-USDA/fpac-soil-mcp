# Quickstart Guide: FPAC Soil MCP Server

Get up and running with the **FPAC Soil MCP Server** in less than two minutes.

---

## 1. Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended)

---

## 2. Instant Local Run

```powershell
# Clone the repository
git clone https://github.com/AndrewBrown-USDA/fpac-soil-mcp.git
Set-Location fpac-soil-mcp

# Sync environment
uv sync

# Run the server directly (stdio mode)
uv run fpac-soil-mcp
```

---

## 3. Connect to Claude Desktop

Open your Claude Desktop configuration file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the server definition:

```json
{
  "mcpServers": {
    "fpac-soil": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\workspace\\fpac-soil-mcp",
        "run",
        "fpac-soil-mcp"
      ]
    }
  }
}
```

Restart Claude Desktop. Look for the hammer 🔨 icon indicating active tools.

---

## 4. Try These Prompts in Your LLM

Once connected, ask your assistant:

1. **Point Screening Query:**
   > *"What is the USDA soil map unit and farmland classification at latitude 41.8781, longitude -93.0977?"*

2. **Mukey Query:**
   > *"Look up SSURGO map unit details for mukey '408013'."*

3. **FPPA Scope & Legal Rules:**
   > *"Explain the difference between this soil classification lookup and an official FPPA Form AD-1006 determination under 7 CFR Part 658."*

4. **Farmland Classification Definitions:**
   > *"List all official USDA NRCS farmland classification categories and their FPPA significance."*

---

## 5. Development & Testing

```powershell
# Run unit tests
uv run pytest

# Check code quality
uv run ruff check .
```
