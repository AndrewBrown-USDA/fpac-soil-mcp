# Evaluation Event Capture Contract

## Status and scope

This contract defines eval-only capture for Pi subprocess runs. It governs
evidence retention, privacy, artifact naming, diagnostics, and cleanup. It
does not change production logging, HTTP retry instrumentation, workflow
events, or a general event bus.

The contract preserves the existing human-readable summary and structured-tool
semantics. A captured stream is evidence for inspection; it is not itself a
production audit record or an official FPPA determination.

## Identity and metadata

Every capture is associated with:

- `run_id`: an opaque, generated identifier for one evaluator invocation.
- `case_id`: the stable prompt-test case identifier.
- `attempt`: a positive integer beginning at `1`; retries receive distinct
  attempt records and never overwrite an earlier attempt.
- `started_at_utc` and `ended_at_utc`: timezone-aware UTC timestamps in
  RFC 3339/ISO 8601 form.
- `model` and `provider`: normalized, non-secret labels.
- `transport`: the eval transport label, normally isolated `stdio`.
- `return_code` or an explicit terminal outcome such as `timeout` or
  `startup_error`.

Optional metadata is limited to safe operational values:

- an executable name and normalized command template with prompts, arguments,
  tokens, environment values, and generated output removed;
- a revision identifier such as a validated short commit SHA;
- evaluator version/schema version;
- bounded byte and line counts, truncation flags, and retry number.

Secrets, access tokens, environment dumps, user identity, prompt text,
coordinates, geometry, producer information, and generated response content
are not metadata.

## Artifact root and filenames

Persistence is allowed only when the caller explicitly enables the capture
switch (for example, `EVAL_CAPTURE_ARTIFACTS=1`) and supplies or accepts an
artifact root outside the repository. The implementation must reject or
disable retention when the resolved root is inside the repository, a source
tree, or a prompt/fixture directory.

The layout is:

```text
<external-artifact-root>/<run_id>/<case_id>/attempt-<N>/
  metadata.json
  stdout.txt
  stderr.txt
  events.jsonl
  malformed-lines.txt
```

`run_id`, `case_id`, and attempt directory names are generated or validated
opaque identifiers. Filenames use only a conservative ASCII allow-list
(`A-Z`, `a-z`, `0-9`, `_`, `-`, and `.`); prompt text, coordinates, geometry,
producer names, or arbitrary model output must never enter a path. Diagnostic
results expose sanitized relative artifact paths or a root-relative path
reference, never an unsanitized command or raw stream.

## Stream separation and parsing

Capture keeps these channels distinct:

- `stdout`: bounded raw stdout bytes/text, including lines that are not JSON.
- `stderr`: bounded raw stderr bytes/text, kept separate from stdout.
- `events.jsonl`: only complete lines that parse as JSON objects/values under
  the existing parser semantics; normalized event summaries may be recorded
  separately from raw input.
- `malformed-lines.txt`: non-JSON or invalid JSON lines, with line order and
  bounded content preserved for diagnosis but never promoted to tool evidence.

Malformed lines, prose, prompt echoes, and generated answers never count as
structured tool execution. Parsing failures must be represented explicitly;
they must not be silently discarded or converted into successful events.

## Evidence and diagnostics

The normalized result retains the current status and human-readable summary,
and may add:

- `run_id`, `case_id`, and attempt summaries;
- bounded event and malformed-line counts;
- `evidence_classification`, one of:
  - `absent`: no dedicated structured tool evidence was detected;
  - `present_unrecognized`: dedicated structured tool evidence exists, but
    normalized extraction found no recognized tool;
  - `recognized`: a dedicated structured event identifies a recognized tool.
- sanitized artifact path fields for stdout, stderr, JSONL, malformed lines,
  and metadata when retained;
- truncation and cleanup status.

Only dedicated structured tool fields/events can produce `recognized` or
`present_unrecognized`. Prose must remain `absent`, even when it names an
expected tool or contains a tool-like result. Artifact paths identify where
evidence can be inspected; diagnostics must not embed raw captured content.

## Opt-in retention and default behavior

Capture in memory may support diagnostics, but persistence is opt-in and
non-retaining by default. With the switch disabled, no capture artifacts,
repository-local files, or durable raw streams are created. A caller that
enables retention accepts responsibility for the selected external root and
its access controls.

Successful, failed, timeout, startup-error, malformed-JSON, partial-output,
and retry attempts follow the same contract. A missing completed-process object
does not justify dropping available partial stdout/stderr.

## Bounds, retries, and cleanup

All streams, line lengths, parsed-event counts, and metadata fields have
explicit finite limits. On overflow, retain the prefix or bounded record,
set a truncation indicator, and continue diagnostics without unbounded memory
or disk growth. Limits are implementation configuration, not permission to
persist unlimited data.

Each retry is stored under its own attempt identifier while the run remains
bounded by a maximum attempt count and aggregate byte/event budget. Cleanup
must be explicit, deterministic, and safe against path traversal: remove only
artifacts beneath the validated external root, report failures, and never
delete unrelated files. Cleanup should run for temporary/ephemeral capture and
be available for explicitly retained artifacts.

## Privacy and redaction requirements

Sanitize before persistence; field-name matching alone is insufficient.

1. Apply the existing prohibited-key policy for personal and producer data.
2. Inspect free-form strings and redact or suppress values that resemble
   names, email addresses, phone numbers, addresses, identifiers, secrets,
   tokens, credentials, or other sensitive personal data, regardless of key.
3. Redact coordinates, bounding boxes, geometry, WKT/GeoJSON, parcel details,
   and other location-bearing values unless a separately approved fixture
   policy provides a non-sensitive surrogate.
4. Never persist prompts, tool arguments, generated responses, full
   environment variables, authorization headers, cookies, or producer data.
5. Prefer omission or stable placeholders such as `[REDACTED]`; do not attempt
   reversible masking.
6. Treat malformed lines and stderr as sensitive too; they require the same
   redaction before persistence.
7. Keep checked-in fixtures minimal, sanitized, deterministic, and based on
   verified captured failure shapes. The aggregate historical transcript does
   not establish raw Pi envelopes, so no envelope-specific historical claim
   may be inferred from it.

Raw-vs-summary distinction: raw streams are ephemeral by default and may be
retained only after sanitization and explicit opt-in. Summaries and counts may
be returned to the evaluator, but they must not include prohibited raw values.

## Required contract checklist

- [x] Run, case, and attempt IDs are required.
- [x] UTC start/end timestamps are required.
- [x] Model and provider labels are defined.
- [x] Safe command/revision metadata is bounded and sanitized.
- [x] stdout, stderr, parsed JSONL, and malformed lines are separate.
- [x] Artifact root and filename rules prevent repository-local/path-injected
      retention.
- [x] Persistence is explicit opt-in and non-retaining by default.
- [x] Size, event, attempt, truncation, and retry bounds are required.
- [x] Cleanup behavior is explicit and path-safe.
- [x] Diagnostics expose sanitized artifact paths without raw content.
- [x] Raw streams are distinguished from normalized summaries.
- [x] Prohibited keys, free-form sensitive values, and coordinates are
      conservatively redacted.
- [x] Prompts, arguments, responses, and producer data are prohibited from
      persistence.
- [x] Prose and malformed lines never count as tool evidence.
- [x] Success and all specified failure/partial-output paths are covered.
