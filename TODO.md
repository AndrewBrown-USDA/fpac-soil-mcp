# TODO

## Goal
Resolve all three open review threads on PR #55 by correcting sentinel and coverage aggregation behavior and adding executable raw-row fixtures for the new SDV rating strategies.

## Tasks

### 1. Inspect the reviewed aggregation paths
- [x] Read the SDA aggregation SQL, rating parsing, and existing SDV/CPI test fixtures.
- [x] Map each review comment to the smallest required code and test changes.

### 2. Correct CPI sentinel aggregation
- [x] Exclude CPI registry sentinel values before usable-component counts and weighted averages.
- [x] Keep excluded sentinel components out of `rated_pct` while preserving valid CPI behavior.
- [x] Add an executable CPI fixture covering sentinel plus NULL components and verify the expected unrated/rated result.

### 3. Preserve AWS coverage arithmetic
- [x] Update AWS aggregation so NULL-valued components remain in total coverage while excluded from rated values.
- [x] Add executable fixtures for partially rated and all-null AWS map units with independently calculated expected coverage and rating results.

### 4. Add raw-row strategy fixtures
- [ ] Add executable raw-row fixtures for Storie grouping and tie handling.
- [ ] Add executable raw-row fixtures for AWS depth clipping and NULL horizons.
- [ ] Add executable raw-row fixtures for crop-yield weighting and unit detection.
- [ ] Assert independently calculated expected outputs rather than only SQL fingerprints or pre-aggregated rows.

### 5. Validate the review fixes
- [ ] Run the focused SDV contract and strategy tests.
- [ ] Run the repository lint, format, and offline test checks relevant to the changed files.
- [ ] Create a separate Conventional Commit for each logically independent fix.

## Notes
- Scope is limited to the three open review threads on PR #55.
- Preserve existing public response contracts, provenance, caveats, and unrelated worktree changes.
