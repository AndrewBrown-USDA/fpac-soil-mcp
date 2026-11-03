# State 43 — Phase 4 Criterion 2 Close-out

## Baseline Checklist

- [x] `uv run pytest -m "not live_network" -q` — 599 passed, 3 skipped, 42 deselected.
- [x] `uv run ruff check .` — passed.
- [x] `uv run ruff format --check .` — 528 files already formatted.
- [x] `uv run pytest -m live_network -q` — 41 passed, 1 failed, 3 skipped, 599 deselected; failure is pre-existing SDA live query “session is in the kill state” for `test_live_dynamic_sdv_queries_and_unrated_water_urban`.

## Wave Board

| Task | Wave | Status |
|---|---:|---|
| 43.1.1 | 1 | done |
| 43.1.2 | 1 | done |
| 43.2.1 | 2 | done |
| 43.3.1 | 3 | done |
| 43.4.1 | 4 | done |

## Task Reports

<!-- Append one concise report per task: status, files, commands/results, deviations, commit. -->

## 43.1.1

- **Status:** done; added the Criterion 2 site/corridor scoring contract,
  bounded ratio semantics, provenance/version fields, and unavailable handling.
- **Validation:** `uv run pytest tests\test_lesa.py -k "criterion or site_assessment or lesa" -q` — 37 passed; targeted Ruff passed.
- **Commit:** `82dc460` (`feat(lesa): add criterion two scoring contract`).
- **Deviations:** none.

## 43.1.2

- **Status:** done; added typed TIGERweb perimeter evidence with geodesic
  perimeter ratios and explicit measured/unavailable/error states.
- **Validation:** `uv run pytest tests\test_tigerweb_client.py tests\test_geometry.py -q` — 37 passed; Ruff and format checks passed.
- **Live:** no new live test was required; the baseline live suite has the recorded pre-existing SDA failure.
- **Commit:** `00776c2` (`feat(tigerweb): add perimeter evidence`).
- **Deviations:** none.

## Wave 1 Gate

- Offline: `uv run pytest -m "not live_network" -q` — 606 passed, 3 skipped,
  42 deselected.
- Ruff and formatting passed; 530 files already formatted.
- Live: `uv run pytest -m live_network -q` — 42 passed, 3 skipped,
  606 deselected.

## 43.2.1

- **Status:** done; integrated Criterion 2 evidence and scoring through site and
  buffered-corridor LESA paths with explicit override and unavailable semantics.
- **Validation:** focused LESA/polygon/corridor tests — 96 passed; phase contract
  tests — 11 passed; targeted Ruff and formatting passed.
- **Commit:** `902f68b` (`feat(lesa): integrate perimeter evidence`).
- **Deviations:** none; `fppa_tools.py` was not modified.

## Wave 2 Gate

- Offline: `uv run pytest -m "not live_network" -q` — 608 passed, 3 skipped,
  42 deselected.
- Ruff and formatting passed; 531 files already formatted.
- Live: `uv run pytest -m live_network -q` — 42 passed, 3 skipped,
  608 deselected.

## 43.3.1

- **Status:** done; added site/corridor Criterion 2 contract coverage,
  unavailable-vs-zero assertions, boundary cases, and opt-in TIGERweb coverage.
- **Validation:** focused contracts/live tests — 13 passed, 3 deselected;
  offline suite — 612 passed, 3 skipped, 43 deselected; Ruff/format passed.
- **Live:** TIGERweb coverage passed; the full live suite had one unrelated
  pre-existing SDA “session is in the kill state” failure.
- **Commit:** `98e328f` (`test(lesa): cover criterion two contracts`).
- **Deviations:** none.

## Wave 3 Gate

- Targeted TIGERweb live tests passed; the unrelated SDA live failure is recorded
  explicitly and does not block the offline or Criterion 2 verification.

## 43.4.1

- **Status:** done; closed Phase 4 Criterion 2 documentation for site and
  corridor workflows and linked the next server work to the Phase 8 map
  envelope / Track A M3, which precedes M4.
- **Files:** `planning\MASTER_PLAN.md`, `planning\STATE_43.md`,
  `planning\tasks\43.4.1.todo.md`.
- **Validation:** `uv run pytest -m "not live_network" -q` — 612 passed,
  3 skipped, 43 deselected; `uv run ruff check .` and
  `uv run ruff format --check .` passed. Focused Criterion 2 contract/live
  tests also passed.
- **Live limitation:** the full live suite retains the pre-existing SDA
  failure in `test_live_dynamic_sdv_queries_and_unrated_water_urban` (“session
  is in the kill state”); TIGERweb coverage passed.
- **Deviations:** no public metadata change was required; historical planning
  records were preserved. Criterion 2 remains preliminary evidence and does
  not produce an official FPPA determination, official LESA score, Form
  AD-1006, or NRCS-CPA-106.
