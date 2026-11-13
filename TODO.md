# TODO

## Goal
Fix the two open PR #98 review findings in the shared evaluation corpus validator and verify both fixes.

## Tasks

### 1. Validator fixes and regression tests
- [ ] Accept `"null"` as an `expected_result` schema type in `eval/common/dataset.py`; add a test that a nullable schema validates and keep unsupported types rejected.
- [ ] Validate invocation shapes by kind: resources require exactly `kind` and a non-empty `uri`; tools and prompts require exactly `kind`, a non-empty `name`, and object-valued `arguments`.
- [ ] Add regression coverage for valid tool, resource, and prompt invocations and malformed resource/tool/prompt shapes.

### 2. Validation and implementation commit
- [ ] Run `uv run pytest eval/common/test_common_dataset.py`, `make check`, and `git diff --check`.
- [ ] Review and commit only the validator and test changes in one focused Conventional Commit.

## Notes
- Work on the current PR head branch `refactor/eval-corpus1`; do not fetch, rebase, merge, or push.
- The user chose to track and commit this plan separately before implementation.
- Preserve prior planning changes and `.worktrees/`; do not stage unrelated existing files or post PR replies.
- Draft replies were prepared in `planning/TODO_20261113-2.md`; posting remains outside this implementation request.
