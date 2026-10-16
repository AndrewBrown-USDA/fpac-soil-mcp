# Eval Capture Contract 29

This contract defines the boundary for exact evidence retained by the local
evaluation harness. It does not change the FPAC Soil MCP Server's
public/production payload privacy behavior.

## Retention modes

- Raw retention is **disabled by default**. A run must explicitly opt in to
  raw eval-artifact retention; ordinary evaluation and production execution do
  not persist raw streams or events.
- Raw retention is an eval-harness exception for local diagnostic work only.
  It is not a public MCP response, a production log, an API contract, or an
  authorization to bypass `privacy.py`, Section 1619 protections, or payload
  sanitization.
- Opt-in mode must warn the operator that retained data may contain sensitive
  prompt, tool, provider, model, and environment data. The operator is
  responsible for access control, handling, and cleanup.

## Root and path safety

- The raw-artifact root must be explicitly supplied or resolved outside the
  repository and must be repository-independent. Repository-local roots,
  checkout-relative roots, and paths that resolve inside the repository are
  prohibited.
- Raw artifacts must never be checked in, added to fixtures, or committed to
  repository history. Checked-in fixtures and examples must remain sanitized.
- Run and case identifiers are untrusted input. Before path construction,
  identifiers must be reduced to safe identifiers; `.`, `..`, separators,
  drive/UNC syntax, empty values, and equivalent traversal forms must not
  select directories or escape the external root.
- Artifact paths may be surfaced as bounded diagnostics, but diagnostics must
  not include raw prompt, tool, provider, or model content.

## Evidence and bounded copies

- Complete in-memory/evaluation evidence is distinct from any bounded artifact
  copy. Tool and keyword evaluation must use the complete captured evidence
  available to the harness, including data arriving after an artifact-copy
  limit.
- A bounded diagnostic copy may truncate raw streams or events for practical
  storage limits. It must record that truncation occurred and preserve enough
  metadata to identify the affected copy.
- Truncation indicators apply only to bounded copies; they must not imply that
  the complete evaluation evidence was truncated or sanitized.
- Raw opt-in retention preserves the exact interrogable capture required by
  the evaluation workflow, subject to operator-controlled storage and
  cleanup. It must not be confused with normalized, sanitized diagnostics.

## Privacy and cleanup boundary

- Public and production payloads continue to use the centralized privacy
  decision: prohibited personal fields are rejected or removed through
  `privacy.py`, and public responses remain sanitized.
- Local raw eval evidence is a separately governed diagnostic copy. It may
  contain sensitive values because the operator explicitly enabled retention;
  that exception does not relax public payload validation, response
  sanitization, coordinate privacy expectations, or Section 1619 handling.
- Operators must protect an external raw-artifact root as sensitive data,
  avoid sharing it, and delete retained artifacts when interrogation is
  complete. The harness must not assume repository cleanup or silently copy
  raw material into repository-local diagnostics.

## Required boundary terms

The supported implementation therefore has all of these properties:

1. raw retention is explicit opt-in and warned;
2. the retention root is external to and independent of the repository;
3. identifiers and artifact paths are safe against traversal;
4. bounded copies expose truncation metadata while complete evidence remains
   available for evaluation;
5. checked-in fixtures are sanitized and raw repository use is prohibited;
6. public/production payload sanitization remains unchanged; and
7. cleanup and protection of retained raw evidence remain the operator's
   responsibility.
