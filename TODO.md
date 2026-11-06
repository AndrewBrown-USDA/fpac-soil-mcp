# TODO

## Goal
Add an MCP tool that computes validated USDA NASS Cropland Data Layer (CDL) categorical histograms for an area of interest through the NASS CDL ImageServer, providing recent mapped agricultural-land-cover evidence without presenting it as definitive agricultural use or an official FPPA/LESA determination.

## Tasks

### 1. Define the CDL evidence contract
- [x] Specify validated AOI geometry, optional product/year selection, qualifying CDL classes, coverage, histogram, nodata, and provenance fields in Pydantic response models.
- [x] Define explicit statuses for successful, unavailable, invalid, ambiguous, and upstream-error results.
- [x] Preserve the distinction between recent mapped land-cover evidence, SSURGO farmland classification, NASS county context, and official FPPA/LESA conclusions.

### 2. Implement dynamic ImageServer discovery
- [x] Add a resilient HTTP client for the configured NASS CDL ImageServer endpoint.
- [x] Retrieve and validate service metadata before analysis, including capabilities, spatial reference, categorical raster properties, extent, pixel size, and response provenance.
- [x] Inspect available catalog/time metadata without assuming a fixed year field, mosaic rule, resolution, or enabled operation.
- [x] Add bounded metadata caching with retrieval time and response hash.

### 3. Implement AOI histogram analysis
- [x] Implement the preferred `computeStatisticsHistograms` request with server-side geometry transformation and validated categorical output parsing.
- [x] Validate histogram classes, pixel counts, nodata, coverage, selected product vintage, and reproducibility before returning measured evidence.
- [x] Return explicit structured errors for unsupported operations, invalid geometries, out-of-extent AOIs, malformed responses, and upstream failures.
- [x] Keep local raster download or `exportImage` fallback out of the initial implementation unless the contract tests demonstrate that the preferred operation cannot provide reliable results.

### 4. Expose and register the MCP tool
- [x] Add the public CDL histogram tool under the appropriate tool module with input validation and the standard regulatory limitation notice.
- [x] Register the tool through the centralized tools registrar and include source/method metadata in every public response.
- [x] Add supported endpoint and configuration settings without allowing arbitrary URLs or user-supplied query passthrough.

### 5. Add regression and contract coverage
- [x] Add mocked HTTP tests for metadata discovery, catalog/year handling, successful histograms, nodata and partial coverage, malformed responses, HTTP failures, request exceptions, invalid geometry, and out-of-extent AOIs.
- [x] Add MCP contract coverage proving the tool is discoverable and its response preserves evidence status, provenance, and limitations.
- [x] Assert that CDL evidence does not automatically award Criterion 2 points or claim confirmed active agricultural use.

### 6. Document and validate the change
- [x] Update README, manifest, server metadata, and configuration documentation for the new tool and its evidentiary limits.
- [x] Update the planning documentation to identify the CDL integration as preliminary current-land-cover evidence and retain the need for authoritative agricultural-land-use integration before verified Criterion 2 scoring.
- [x] Run focused CDL tests, the offline test suite, Ruff lint, and format checks; the equivalent checks pass, but the canonical `make check` target could not run because `make` is unavailable in the active Git Bash environment.
- [x] Review the final diff and confirm no remote issue or pull-request state is modified.

## Notes
- Issue: GitHub `#78`, “Add NASS CDL tool into MCP server”.
- Primary source: USDA NASS CDL ImageServer at `https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer`.
- Preferred operation: `computeStatisticsHistograms`; metadata discovery is mandatory before selecting analysis parameters.
- Scope is the initial histogram prototype described in `planning/RESEARCH_CDL_IMAGESERVER_CRITERION_2.md`.
- Do not label CDL classifications as confirmed active agricultural use, ownership, legal agricultural status, FPPA farmland status, or official NRCS/LESA findings.
- Use existing HTTP client, geometry validation, Pydantic, MCP registration, and mocked transport patterns where applicable.
