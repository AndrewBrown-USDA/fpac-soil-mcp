# STATE 50: Guided AD-1006 Interview and CDL Map Context

Resume point for orchestration 50. Plan: `planning/EXECUTION_PLAN_50.md`.
Worker prompt: `planning/PROMPT_TEMPLATE_50.md`.

## Baseline (record before wave 1)

Recorded 2026-11-12 on branch `feature/sa-checklist1` at `d8a78df`.

- [x] Root CDL/LESA subset:
  `uv run --group dev pytest tests/test_cdl_models.py tests/test_cdl_client.py
  tests/test_cdl_tools.py tests/test_lesa.py
  tests/test_site_assessment_contract.py -q` — 109 passed.
- [x] Site Assessment resource/prompt subset:
  `uv run --group dev pytest tests/test_site_assessment_resource.py
  tests/test_prompts.py -q` — 9 passed.
- [x] Agent-app tests:
  `uv run --frozen --python 3.11 pytest tests -q` from
  `apps\agent-fpac-soil-openai-sdk` — 177 passed.
- [x] Agent-app Ruff check and format check on owned files — all checks
  passed; 16 files already formatted.
- [x] Frontend `npm ci`, read-only Biome lint, and production build — passed.
  Baseline output included 10 lint warnings and npm audit reported 10 existing
  findings (4 low, 6 moderate); do not fix them in this plan.
- [ ] Full root `make check` — not run before wave 1.
- [ ] Live-network suite — not run before wave 1.
- [ ] Local browser walkthrough — not run before wave 1.
- [!] `make app-check` could not start because the installed Windows GNU Make
  exits with an Rtools path error. Its equivalent direct app test and Ruff
  commands passed; use direct commands if the local Make executable remains
  unusable.
- [!] `uv run python scripts\fetch_ecfr.py --check` reports title 7 Parts 657
  and 658 XML differs from the manifest. Task 50.1.1 must refresh generated
  files and verify the registry before guided scoring.

## Wave Board

| Wave | Task | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | 50.1.1 Refresh eCFR references and verify Site Assessment registry | pending | | Registry conflict blocks 50.2.1; do not silently edit scoring. |
| 1 | 50.1.2 Add combined CDL context analysis | pending | | Keep existing histogram tool compatible. |
| 1 gate | eCFR and CDL contract gate | pending | | |
| 2 | 50.2.1 Add resource-backed conversational Site Assessment flow | pending | | Requires both Wave 1 tasks and no unresolved eCFR conflict. |
| 2 | 50.2.2 Add CDL map overlay and summary display | pending | | CORS failure blocks overlay; ask before proxy work. |
| 2 gate | Chat/map integration gate | pending | | |
| 3 gate | Serial validation and local browser walkthrough | pending | | No deployed dev-app trial. |

## Task Reports
