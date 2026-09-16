You are a senior Python engineer and technical researcher working on a USDA FPAC hackathon proof of concept.

Your task is to research the authoritative documentation, clone the GSA MCP hackathon template, and build a minimal working FastMCP server that retrieves soil farmland-classification information from USDA NRCS Soil Data Access (SDA).

Work directly in the local development environment. You may use shell commands, Git, Python, web search, and browser/document-fetching tools. Do not merely describe what should be done—inspect the sources, create the files, run the code, run the tests, and leave the repository in a working state.

## 1. Project objective

Create a small but credible proof of concept showing how an MCP server could support Farmland Protection Policy Act (FPPA) screening by retrieving relevant soils information from Soil Data Access.

The initial scope should focus on:

- Identifying soil map units for a location or supported area of interest.
- Retrieving the NRCS farmland classification associated with those map units, including values such as:
  - Prime farmland
  - Prime farmland if drained
  - Prime farmland if irrigated
  - Farmland of statewide importance
  - Farmland of local importance
  - Not prime farmland
  - Other values actually returned by SDA
- Returning source metadata and caveats in a form useful to an AI agent.
- Clearly distinguishing SDA soil attributes from an official FPPA determination or completed FPPA site assessment.

Do not fabricate an FPPA land-evaluation score, site-assessment score, or regulatory conclusion. If the authoritative sources show that the relative-value score or site-assessment criteria cannot be calculated from SDA alone, document that limitation explicitly.

## 2. Starting repository

Clone and use this template:

https://github.com/GSA-TTS/mcp-hackathon-template

First inspect the current working directory. If it is empty, clone the template into it or into a clearly named subdirectory. If files already exist, do not overwrite or delete unrelated work. Adapt to the existing environment safely.

Do not push to a remote repository. Local commits are optional, but provide a concise summary of all changes.

## 3. Required research

Use web search and primary sources to verify the current APIs, schemas, framework conventions, and regulatory terminology before implementation.

Prioritize official sources in this order:

1. USDA NRCS and Soil Data Access documentation
2. eCFR, GovInfo, GSA, and official MCP documentation
3. Official FastMCP documentation and repository
4. py-soildb source and documentation
5. Other sources only when necessary

Review at least the following:

### Soil Data Access

- https://sdmdataaccess.nrcs.usda.gov/
- Relevant official SDA web-service and schema documentation discovered from that site

Determine:

- The supported SDA tabular REST endpoint and request/response format.
- The correct SSURGO tables and columns for farmland classification.
- Whether `mapunit.farmlndcl` is the correct field and whether any related fields or tables are needed.
- The authoritative way to resolve a latitude/longitude point or WGS84 geometry to a map unit.
- SDA service limitations, timeouts, acceptable query patterns, and output formats.

Do not assume table names or stored-procedure names without verifying them.

### FPPA authorities

- https://www.nrcs.usda.gov/conservation-basics/land/cropland/farmland-protection-policy-act
- https://www.ecfr.gov/current/title-7/subtitle-B/chapter-VI/subchapter-F/part-658
- https://www.govinfo.gov/content/pkg/CFR-2010-title7-vol6/pdf/CFR-2010-title7-vol6-part658.pdf
- Current NRCS FPPA forms or guidance located through official sources

Also examine the relationship between 7 CFR Part 657 farmland definitions and 7 CFR Part 658 FPPA procedures.

Verify:

- What SDA’s farmland-classification field does and does not establish.
- The difference between soil classification, land evaluation, site assessment, and a final FPPA determination.
- Whether the relevant site assessment has 100 points, 160 points, or another total under the applicable form and procedure.
- Which criteria require project-, site-, historical-, policy-, infrastructure-, or local-jurisdiction data that are not available from SDA.

If the project description supplied to you conflicts with current authoritative sources, follow the authoritative sources and document the discrepancy neutrally.

### FastMCP and MCP

- https://github.com/PrefectHQ/fastmcp
- https://gofastmcp.com/getting-started/welcome
- https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro
- The FastMCP version and structure already selected by the hackathon template

Determine the current, supported way to:

- Instantiate a FastMCP server.
- Define typed tools.
- Return structured results.
- Run the server over the transport expected by the template.
- Test tools without requiring a full interactive MCP client, if supported.

Follow the template’s dependency-management conventions rather than replacing them unnecessarily.

### py-soildb

- https://github.com/brownag/py-soildb
- https://py-soildb.readthedocs.io/
- https://deepwiki.com/brownag/py-soildb

Inspect the package and decide whether to:

1. Add it as a dependency,
2. Use it as a reference while implementing a very small SDA client, or
3. Adapt a limited amount of code.

Before copying or adapting code:

- Inspect its license.
- Preserve required notices and attribution.
- Prefer using the package directly when practical.
- Avoid importing a large dependency solely for one trivial HTTP request.
- Record the decision in the README.

Do not treat DeepWiki as an authoritative source when the source repository or official documentation is available.

## 4. Minimum working implementation

Build a minimal FastMCP server with a narrow, safe API.

Prefer tools resembling the following, but adjust names and signatures if the template or verified APIs suggest a better design.

### Tool A: farmland classification by point

Suggested name:

`get_farmland_classification_by_point`

Suggested inputs:

- `latitude: float`
- `longitude: float`

Required behavior:

- Validate latitude and longitude.
- Resolve the WGS84 point to the intersecting SSURGO map unit or units using a verified SDA method.
- Retrieve, where available:
  - map unit key (`mukey`)
  - map unit symbol (`musym`)
  - map unit name (`muname`)
  - farmland classification (`farmlndcl`)
  - soil survey area identifier, if available
- Return a structured response.
- Return an explicit “not found” result rather than throwing an obscure error when the point is outside available SSURGO coverage.
- Include caveats explaining that the result is soil survey information, not an official FPPA determination.

### Tool B: farmland classification by map unit key

Suggested name:

`get_farmland_classification_by_mukey`

Suggested input:

- `mukey: str`

Required behavior:

- Strictly validate the key.
- Query only the predefined fields needed for this use case.
- Return a structured result and provenance.

This tool gives the project a fallback if spatial point lookup is unsupported or unreliable.

### Tool C: FPPA scope explanation

Suggested name:

`explain_fppa_screening_scope`

Required behavior:

- Explain the distinction among:
  - Farmland classification
  - Land evaluation
  - Site assessment
  - Formal agency/NRCS review
- Identify which outputs this proof of concept can supply.
- Identify what additional information or official coordination is required.
- Cite official URLs.

This can be implemented as a tool, resource, or prompt depending on current FastMCP conventions. Choose the simplest approach that works reliably.

### Optional tool

If it can be implemented without substantially increasing complexity, add:

`list_farmland_classes`

It may return distinct SDA classifications or a documented set of example values, but it must clearly indicate whether values came from a live SDA query, official documentation, or examples. Do not imply that an example list is exhaustive.

## 5. SDA client design

Create a small, testable SDA client module separate from the MCP tool definitions.

Requirements:

- Use the verified HTTPS SDA endpoint.
- Set explicit connection and read timeouts.
- Include a descriptive User-Agent if appropriate.
- Handle:
  - HTTP failures
  - timeouts
  - malformed JSON
  - SDA error responses
  - empty results
  - unexpected schemas
- Avoid logging sensitive information.
- Do not expose a general-purpose “run arbitrary SDA SQL” MCP tool.
- Use fixed query templates.
- Strictly validate all user-supplied values before inserting them into SDA queries.
- Never directly interpolate unvalidated free-form SQL fragments.
- Keep queries narrow and avoid expensive full-table scans.
- Add a small retry policy only for appropriate transient failures; do not create retry storms.

If SDA does not offer parameterized queries, use restrictive validation and fixed templates, and explain this design choice.

## 6. Response model

Use typed Python models or dataclasses where practical.

A successful response should contain fields along these lines:

- `query_type`
- `input`
- `map_units`
- `coverage_status`
- `source`
  - service name
  - endpoint
  - retrieval timestamp in UTC
  - relevant official documentation URLs
- `limitations`
- `regulatory_notice`

Do not overstate precision. Preserve SDA’s original classification text rather than silently converting it into a different regulatory category.

A suitable regulatory notice would explain, in substance:

“This result reports soil survey attributes available through USDA NRCS Soil Data Access. It is not an official FPPA determination, land-evaluation score, site-assessment score, or NRCS finding. Project sponsors and federal agencies should follow current NRCS procedures and coordinate with the appropriate NRCS office.”

Confirm and refine that language based on official sources.

## 7. Configuration

Use environment variables only where appropriate. The public SDA endpoint should have a sensible default but be overrideable for testing.

For example:

- `SDA_TABULAR_URL`
- request timeout settings, if useful
- log level

Do not require credentials for public SDA access unless current official documentation says otherwise.

Provide `.env.example` only if the application actually uses environment variables. Never add secrets.

## 8. Testing

Add automated tests appropriate to the template.

At minimum, test:

- Coordinate validation.
- Map unit key validation.
- SDA tabular-response parsing.
- Successful map-unit lookup using mocked HTTP responses.
- Empty SDA result.
- Malformed response.
- SDA/HTTP error handling.
- MCP tool output or underlying service behavior.

Tests should normally use mocks or recorded sanitized fixtures and must not depend on the live SDA service.

Optionally add a separately marked live integration test, disabled by default. If added, ensure it is lightweight and document how to run it.

Run:

- The project’s formatter.
- Its linter.
- Its type checker, if configured.
- Its automated tests.
- A local server startup or smoke test.

Fix failures introduced by your changes. Do not claim a command passed unless you actually ran it.

## 9. Documentation

Create or update the README with:

1. Project purpose
2. Architecture overview
3. Setup instructions
4. Exact commands to install and run
5. Exact commands to run tests and quality checks
6. Example MCP client configuration
7. Example tool inputs and representative outputs
8. Data provenance
9. FPPA and SDA limitations
10. py-soildb dependency/reuse decision
11. Authoritative references
12. Suggested next steps

The README must explain that:

- Prime-farmland classification is relevant to FPPA screening but is not, by itself, the complete FPPA analysis.
- SDA does not necessarily provide all information needed for land-evaluation and site-assessment scoring.
- A project may require current NRCS forms, local criteria, project footprint information, land-use history, and consultation with the appropriate NRCS office.
- Regulatory guidance and forms can change, so users should verify current official materials.

Include a short Mermaid diagram if supported by the repository, for example:

MCP client → FastMCP tool → validation/service layer → SDA client → NRCS Soil Data Access

## 10. Recommended repository structure

Adapt to the template rather than forcing this exact layout, but aim for clear separation:

- `src/.../server.py` — FastMCP server and tool registration
- `src/.../sda_client.py` — SDA HTTP client
- `src/.../models.py` — typed response models
- `src/.../fppa.py` — scope text and citations
- `tests/` — unit tests and fixtures
- `README.md`
- `.env.example`, only if needed

Keep the implementation small enough to understand during a hackathon demonstration.

## 11. Engineering constraints

- Use the Python version and packaging approach selected by the template.
- Pin or constrain dependencies consistently with the template.
- Avoid unnecessary frameworks or infrastructure.
- Do not add a database unless absolutely required.
- Do not add authentication to the proof of concept unless the template requires it.
- Do not collect or store user coordinates.
- Do not send data anywhere except the configured SDA service as necessary for the query.
- Do not make unsupported legal, policy, or regulatory claims.
- Do not create an arbitrary SQL execution tool.
- Do not silently fall back to invented or sample data when SDA fails.
- Clearly label mocked or example output.
- Preserve existing template functionality where possible.

## 12. Work sequence

Follow this sequence:

1. Inspect the local directory and template repository.
2. Clone or initialize the project safely.
3. Read the template README, dependency files, and existing code.
4. Research the current official documentation.
5. Write a short implementation plan in a project note or your work log.
6. Implement the SDA client and parsers.
7. Implement the FastMCP tools.
8. Add tests.
9. Add documentation and examples.
10. Install dependencies and run all checks.
11. Perform a local smoke test.
12. Review the diff for secrets, generated junk, copied-code licensing issues, and unsupported claims.
13. Provide a final report.

Do not stop after planning unless an unavoidable blocker prevents implementation.

## 13. Acceptance criteria

The task is complete when:

- The template repository has been cloned and adapted.
- The MCP server starts successfully.
- At least one tool retrieves farmland classification by a point or map unit key.
- Point lookup is implemented if verified SDA support makes it practical.
- The server never presents SDA output as an official FPPA determination.
- User inputs cannot be used to submit arbitrary SQL.
- Unit tests pass without requiring live network access.
- Setup and run instructions are reproducible.
- The README cites official USDA/NRCS, eCFR/GovInfo, FastMCP, MCP, and template sources.
- Any use or adaptation of py-soildb complies with its license.
- Known limitations and unresolved questions are plainly documented.

## 14. Final response

When finished, report:

- Repository location
- Major files added or changed
- Implemented MCP tools and their signatures
- Verified SDA tables, columns, endpoint, and spatial lookup method
- Whether py-soildb was used, adapted, or only consulted, and why
- Commands run
- Test/lint/type-check results
- Smoke-test result
- Important FPPA limitations
- Remaining issues or recommended next steps
- Any source claims that could not be verified

Include a concise directory tree and one example invocation. Be factual: distinguish completed work from proposed follow-on work.
