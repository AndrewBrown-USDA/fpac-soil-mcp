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

---

# TODO: Live CDL Integration Demo

## Goal
Run a one-off live-feed demo for the CDL histogram MCP tool using a small default Iowa polygon and render the response both as terminal output and a standalone HTML report.

## Tasks

### 1. Run the live demo
- [x] Invoke the existing public CDL tool path against the live NASS CDL ImageServer using a small default Iowa polygon.
- [x] Use only live service responses and the existing production code path; do not use mock data or modify the test suite.
- [x] Keep the demo one-off and avoid adding a new committed demo script or dependency.

### 2. Show live results
- [x] Print status, AOI hash, product vintage, coverage, qualifying percentage, pixel counts, provenance, and histogram bins in a readable terminal summary.
- [x] Write a standalone HTML report with the same live evidence, a proportional histogram visualization, source metadata, and the preliminary-screening limitations.
- [x] Render error, unavailable, invalid, and ambiguous responses visibly without fabricating measurements.

### 3. Validate the live run
- [x] Run the demo against the live feed and confirm the generated HTML report exists.
- [x] Do not add tests or update README documentation for this one-off demonstration.

## Notes
- Use a small Iowa Polygon as the default AOI so the live request remains bounded.
- The demo is observational and must not describe CDL classes as confirmed active agricultural use or an official FPPA/LESA determination.
- Keep the demo separate from the MCP server runtime and do not add `exportImage` or local raster processing.

---

# TODO: CDL Raster Attribute Table Names

## Goal
Extend the production CDL histogram response to include live raster attribute-table class names alongside numeric class values and correctly parse the ImageServer histogram edge metadata.

## Tasks

### 1. Discover and model live RAT metadata
- [x] Query the live ImageServer metadata for its raster attribute table fields and class-name column.
- [x] Add a validated class-name mapping to the production CDL response contract and preserve numeric codes when a name is unavailable.

### 2. Parse and attach class names
- [x] Parse the live ImageServer histogram where `min` and `max` are bin edges such as `-0.5` and `190.5`, deriving integer class codes from count indexes.
- [x] Attach raster attribute-table names to histogram bins without treating names as agricultural qualification evidence.
- [x] Preserve explicit ambiguous/error states when RAT metadata or histogram semantics cannot be verified.

### 3. Run live validation
- [x] Run the production MCP tool against the live Iowa polygon and display numeric class values with RAT names in terminal output and the existing HTML report.
- [x] Do not use mock data, modify the test suite, or update README documentation for this live validation.

## Notes
- Scope is the production MCP response, not only the temporary demo.
- Use the USDA NASS CDL ImageServer as the only data source.
- Do not infer class names from hard-coded CDL tables when the live raster attribute table is unavailable.
- Preserve the preliminary mapped-land-cover limitation and do not award Criterion 2 points from CDL alone.

---

# TODO: PR #79 Review Fixes

## Goal
Resolve all open Copilot and author review findings for the CDL ImageServer histogram tool without reporting unverifiable vintage, histogram semantics, or AOI coverage as measured evidence.

## Tasks

### 1. Verify requested product vintage
- [x] Discover catalog/time metadata using the configured ImageServer and identify the requested `product_vintage` from verified service fields.
- [x] Apply the verified catalog item or mosaic selector to histogram requests and return `unavailable` when the requested vintage cannot be matched or selected.
- [x] Add mocked tests proving different vintages produce different selectors and unverifiable vintages do not produce success.

### 2. Validate histogram semantics
- [x] Require explicit bins or validate count-array `min`, `max`, `size`, integer-centered unit-width buckets, and count length before deriving class values.
- [x] Reject fractional, negative, non-finite, or inconsistent counts without coercing them through `int()`.
- [x] Add regression tests for grouped bins, malformed edges, fractional counts, negative counts, and valid edge-based CDL bins.

### 3. Enforce NoData and coverage boundaries
- [x] Remove effective NoData classes from the qualifying set before marking bins or calculating the agricultural numerator.
- [x] Establish a complete AOI coverage denominator from validated service/pixel metadata, and return `unavailable` when the response cannot prove complete AOI coverage.
- [x] Add tests for NoData configured as qualifying, partial/out-of-extent AOIs, and unavailable coverage metadata.

### 4. Harden metadata and geometry submission
- [x] Reject incomplete or nonnumeric `fullExtent` values before caching them and ensure public extent access cannot raise `KeyError`.
- [x] Extract or reuse the existing Esri ring-winding normalization utility so CDL polygon exteriors are clockwise and holes counterclockwise.
- [x] Add focused tests for incomplete extents and Polygon/MultiPolygon exterior and hole winding.

### 5. Update contract and documentation
- [x] Update CDL response/provenance fields and tool documentation to distinguish verified vintage, complete coverage, ambiguity, and unavailability.
- [x] Preserve the limitation that CDL is mapped land-cover evidence and cannot establish active farming or official FPPA/LESA conclusions.

### 6. Validate the review fixes
- [x] Run focused CDL and geometry tests, then the offline test suite.
- [x] Run Ruff lint and format checks and review the final diff for unrelated changes.

## Notes
- Preserve existing user changes and completed TODO history.
- Keep the configured ImageServer as the only supported source; do not add arbitrary URL or query passthrough.
- Do not modify remote pull-request state or create a commit.

---

# TODO: PR #79 Histogram `size` Review

## Goal
Correct count-array histogram validation to interpret ArcGIS `size` as the number of bins while deriving CDL integer class values only when bins have width one.

## Tasks

### 1. Correct histogram metadata validation
- [x] Require `size` to be a positive integer equal to the count-array length.
- [x] Require the finite range `(max - min) / size` to equal one and retain the half-integer edge alignment needed to map bins to integer class values.
- [x] Derive each class value from its corresponding bin position only after all metadata checks pass.

### 2. Update focused histogram tests
- [x] Change the valid three-count fixture to use `size=3`.
- [x] Add or adjust rejection cases for mismatched size/count length and non-unit bin width.
- [x] Preserve coverage for malformed edges and invalid counts.

### 3. Validate and prepare review response
- [x] Run focused CDL tests and relevant lint/format checks.
- [x] Summarize why requiring unit-width bins preserves exact integer-key mapping without assuming numeric adjacency implies a relationship between CDL classes.

## Notes
- Treat numeric CDL codes as identifiers; neighboring codes are not assumed to be semantically related.
- Do not map any count array to class codes unless its bin geometry supports one-to-one unit-width integer classes.
- Preserve completed TODO history and do not modify remote pull-request state; commit locally only when requested.

## Discovered Tasks

- [x] Address unresolved PR #79 review comment: combine and validate all polygon geometries in FeatureCollections so no requested AOI features are silently ignored; add focused tests.
- [ ] Address unresolved PR #79 review comment: make the configured CDL metadata cache persist across public tool invocations, and add tests proving repeated calls respect the configured TTL.
