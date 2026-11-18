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

Once connected, test the server tools, resources, and prompt templates using these categorized sample queries across all phases:

### Category 1: Discovery, Capabilities & Regulatory Scope
- **Server Discovery & Tool Listing**:
  > *"What tools, resources, and prompt templates do you have available for FPAC-NRCS soil data and FPPA screening?"*
- **Regulatory Boundaries & Scope (`explain_fppa_screening_scope`)**:
  > *"Explain the difference between preliminary SDA soil screening under 7 CFR Part 657 and a formal FPPA LESA determination or Form AD-1006 / NRCS-CPA-106 under 7 CFR Part 658."*
- **SSURGO Farmland Classification Catalog (`list_farmland_classes`)**:
  > *"List all official USDA NRCS SSURGO farmland classification categories, their definitions, and their FPPA protection status."*

### Category 2: Point & Map Unit Lookups (Phase 1)
- **Prime Farmland / Midwest Corn Belt (`get_farmland_classification_by_point`)**:
  > *"What is the USDA soil map unit, farmland classification, and FPPA status at latitude `41.8781`, longitude `-93.0977` (Marshall County, IA)?"*
- **Conditional Prime Farmland**:
  > *"Can you check the soil map unit and farmland classification for latitude `39.7684` and longitude `-87.1581`?"*
- **Urban / Non-Prime Farmland**:
  > *"Can you check the soil map unit and farmland classification for latitude `39.7684` and longitude `-86.1581` (Indianapolis, IN)?"*
- **Direct Map Unit Key (`mukey`) Lookup (`get_farmland_classification_by_mukey`)**:
  > *"Retrieve the official farmland classification and soil map unit details for SSURGO map unit key (mukey) `412850`."*

### Category 3: Polygon AOI & Spatial Screening (Phase 2)
- **Polygon Farmland & NCCPI Screening (`analyze_farmland_by_polygon`)**:
  > *"Analyze the farmland classification and acreage breakdown for this proposed solar farm parcel in Story County, IA:*
  > ```json
  > {
  >   "type": "Polygon",
  >   "coordinates": [[
  >     [-93.6500, 42.0200],
  >     [-93.6300, 42.0200],
  >     [-93.6300, 42.0400],
  >     [-93.6500, 42.0400],
  >     [-93.6500, 42.0200]
  >   ]]
  > }
  > ```
  > *Please check for Census 2020 urban area overlap."*

  `productivity_index` (nccpi, csr2, cpi, or storie) selects the index used for Land Evaluation scoring; NCCPI v3 is always included per map unit as national baseline context. The `include_nccpi` argument was removed (breaking change); calls that still send it are rejected.
- **SSURGO Soil Boundary Vector Geometry Export (`get_soil_polygons_by_geometry`)**:
  > *"Retrieve the clipped SSURGO soil map unit polygon boundaries and properties as a GeoJSON FeatureCollection for the following project boundary:*
  > `POLYGON((-93.65 42.02, -93.63 42.02, -93.63 42.04, -93.65 42.04, -93.65 42.02))`"*

### Category 4: Statutory Urban Exemption & Soil Interpretations (Phase 3)
- **Census 2020 Urban Area Exemption Screening (`check_urban_area_exemption`)**:
  > *"Screen this commercial project site in Des Moines, IA against Census 2020 Urban Area boundaries (Layer 0) to check if it qualifies for an FPPA statutory exemption under 7 CFR § 658.2(a):*
  > `POLYGON((-93.62 41.58, -93.60 41.58, -93.60 41.60, -93.62 41.60, -93.62 41.58))`"*
- **Component Soil Interpretations & NCCPI Ratings (`get_soil_interpretations`)**:
  > *"Retrieve the component-weighted National Commodity Crop Productivity Index (NCCPI v3) ratings for SSURGO map unit keys `412850`, `412851`, and `413100`."*

### Category 5: Multi-County Corridor Analysis & Form NRCS-CPA-106 LESA (Phase 3)
- **Transmission Line Right-of-Way with Laydown Yard (`analyze_corridor_fppa`)**:
  > *"Perform a complete FPPA corridor screening and Form NRCS-CPA-106 LESA evaluation for a proposed 230kV transmission line:*
  > - **Centerline**: `LINESTRING(-93.62 42.02, -93.55 42.08, -93.45 42.15)`
  > - **Corridor Width**: Buffer `75 feet` on each side (150-ft total right-of-way)
  > - **Indirect Staging Yard**: `POLYGON((-93.56 42.07, -93.54 42.07, -93.54 42.09, -93.56 42.09, -93.56 42.07))`
  > - **Site Assessment Inputs**: Project farm tract size is 350 acres.
  > 
  > - **Part VI scoring payload**: Provide `site_assessment_inputs.criteria_inputs` for each non-automated criterion, with an `awarded_points` value and a `justification`. For example:
  >   ```json
  >   {
  >     "site_assessment_inputs": {
  >       "project_farm_acres": 350,
  >       "criteria_inputs": {
  >         "1": {"awarded_points": 8, "justification": "Rural zoning; no urban services."},
  >         "2": {"awarded_points": 7, "justification": "No existing nonfarm development on the tract."},
  >         "3": {"awarded_points": 6, "justification": "No protected lands identified in the project record."}
  >       }
  >     }
  >   }
  >   ```
  > *Please partition by county, query NASS agricultural statistics, apply 7 CFR § 658.5(c) corridor rules (zeroing criteria 5 & 6), and evaluate whether the total LESA score exceeds the 160-point threshold. Supply the remaining applicable criteria in `criteria_inputs`; omitted non-automated criteria default to zero and do not represent an official NRCS determination."*
- **Corridor Alternative Alignment Comparison**:
  > *"Compare two highway bypass alignments for FPPA farmland conversion impact:*
  > - **Primary Alignment**: `LINESTRING(-93.60 42.00, -93.50 42.10)`, buffer 100 feet
  > - **Alternative Alignment B**: `LINESTRING(-93.62 42.00, -93.58 42.06, -93.50 42.10)`, buffer 100 feet
  > *Which route minimizes conversion of Prime Farmland and Farmland of Statewide Importance?"*

### Category 6: Guided Assistant Prompts
- **General FPPA Screening Assistant (`fppa_screening_assistant`)**:
  > *"Use the `fppa_screening_assistant` prompt to evaluate a proposed 50-acre rural water treatment facility in Boone County, IA at `-93.88, 42.05`."*
- **Linear Corridor Assistant (`fppa_corridor_screening_assistant`)**:
  > *"Use the `fppa_corridor_screening_assistant` prompt to guide us through an 18-mile multi-county pipeline right-of-way evaluation under 7 CFR § 658.5(c)."*
- **Urban Exemption Assistant (`fppa_urban_exemption_assistant`)**:
  > *"Use the `fppa_urban_exemption_assistant` prompt to evaluate a proposed logistics park expansion on the fringe of Cedar Rapids, IA."*
- **Site Assessment & Scoring Assistant (`fppa_site_assessment_assistant`)**:
  > *"Use the `fppa_site_assessment_assistant` prompt to evaluate Part VI Site Assessment criteria and Form AD-1006 decision thresholds for a new USDA-funded community health facility."*

---

## 5. Development & Testing

### Databricks Serverless Notebooks

To avoid reinstalling Node/npm and the Databricks MCP libraries every time serverless
compute restarts, open the notebook's Environment pane, choose **Custom** under
**Base environment**, and select
`/Workspace/Users/Groups/team-03/fpac-soil-mcp/databricks/serverless-environment.yaml`.
Databricks caches that environment. Packages installed ad hoc (`%pip`, uv venvs in
`/tmp`) are lost on restart. Change pins in that file by pull request only.

Without a notebook (for example, Genie Code shell commands), run
`source databricks/bootstrap-serverless.sh` from the repository root before using
`node`, `npm`, or `npx`. It installs the same pins in about 20 seconds after a restart
and is an instant no-op otherwise.

### Local Browser Harness

The repository also provides a local browser workbench for inspecting tools, resources,
prompts, and deterministic evaluation cases through the MCP protocol:

```powershell
Set-Location eval\fpac_soil_mcp_harness
npm install
npm start
# open http://127.0.0.1:3030
```

Use `npm run dev` for watch mode or `npm run check` for syntax checks. The default
connection is `stdio`, which launches `uv run fpac-soil-mcp` from the repository root.
For an existing network server, set `MCP_MODE=sse` and
`MCP_URL=http://127.0.0.1:8000/sse`, or set `MCP_MODE=http` and
`MCP_URL=http://127.0.0.1:8000/mcp`.

The harness is local-only and binds to `127.0.0.1` by default. Its Eval Cases tab uses
deterministic invocations and response checks; it does not perform LLM tool selection or
replace the Python/Databricks agent-evaluation paths. Databricks App hosting and
model-based evaluation are separate forthcoming work. Harness results remain preliminary
soil screening and are not official FPPA determinations, LESA scores, Form AD-1006, or
NRCS-CPA-106 decisions.

```bash
# Run unit tests (offline)
uv run pytest -m "not live_network and not agent_eval"

# Check code quality and formatting
uv run ruff check .
uv run ruff format --check .

# Run agent evaluations with pi (requires pi CLI and API keys)
python eval/pi/run_evals.py
```
