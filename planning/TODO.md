# TODO — Resolve redundant corpus checks

## Goal
Remove the corpus-size assertion in `test_common_matching.py` that is implied by its exact-ID and uniqueness assertions, while preserving independently required checks at other consumer boundaries.

## Tasks

### 1. Confirm the invariant
- [x] Verify `EXPECTED_CORPUS_IDS` contains the complete 38-ID set and the test retains both uniqueness and exact-set assertions.
- [x] Confirm the remaining Python dataset and harness loader/HTTP checks serve their distinct entry-point contracts and must remain.

### 2. Remove the redundant assertion
- [ ] Delete only `assert len(ids) == 38` from `test_corpus_ids_cover_all_cases_without_duplicates` in `eval/common/test_common_matching.py`.

### 3. Validate and commit
- [ ] Run `uv run pytest eval/common/test_common_matching.py -q`.
- [ ] Run `git diff --check`, review the exact staged diff, and commit the focused test change as `test(eval): remove redundant corpus count assertion`.
- [ ] Mark completed tasks and commit planning progress separately with a `docs(planning):` message.
- [ ] Archive this plan as `planning/TODO_20261112-1.md` in a separate planning-only commit.

## Notes
- Branch: `refactor/eval-corpus1`; use the current task branch and do not switch branches.
- Planning artifacts are tracked, per user choice. Keep planning commits separate from the test commit.
- Preserve the existing root `TODO.md` and the pre-existing untracked `planning/RESEARCH_ISSUE_88_EVAL_CORPUS_CONSOLIDATION.md`.
- The exact expected-ID set plus the uniqueness assertion imply the 38-row count in this one test. Keep count/uniqueness checks in the dataset, harness-loader, and HTTP smoke tests; they validate separate consumers and are required by Plan 48.
- Do not change runtime code, corpus data, other assertions, or test behavior.
- No remote Git actions are authorized.
