# Production Hardening Sprint 3

Date: 2026-09-30
Baseline: `ea97d75a79727276f77b10121c06692bf39da1a5`

## Goal

Finish the runtime data migration by moving the media catalog out of `movies_cache.json`, eliminate catalog read-modify-write races, and add end-to-end integration coverage for destructive library workflows and restart recovery.

## Checkpoint 1 - SQLite media catalog

- Add a SQLite-backed media catalog with one row per media path and stable ordering.
- Import legacy `movies_cache.json` on first use when the SQLite catalog is empty.
- Preserve existing `load_cache` / `save_cache` API contracts.
- Add transactional catalog mutation helpers and atomic per-item view increments.
- Preserve view increments that occur while a long scanner pass is running.

## Checkpoint 2 - Catalog writers

- Convert /api/play view updates to atomic SQLite updates.
- Convert AI metadata cache updates and media conversion cache rewrites to transactional catalog mutations.
- Convert filesystem delete/rename/move cache updates to transactional mutations where practical.
- Keep full scanner replacement semantics while merging the newest dynamic fields before commit.

## Checkpoint 3 - Integration and recovery tests

- Cover legacy cache migration.
- Cover concurrent view increments.
- Cover scan commit versus concurrent view increment.
- Cover authenticated API flow for catalog listing, rename, move, delete, and diagnostics.
- Cover application restart behavior against persistent SQLite state.
- Simulate catalog write failure after filesystem changes and verify operation journal visibility.

## Checkpoint 4 - Release validation

- Import smoke for runtime dependencies.
- Python compileall.
- Full pytest suite and coverage gate.
- Keep modified/new Python files below 300 lines.
- Use GitHub Actions when available; otherwise use the isolated Railway validator on the exact final branch head.
- Merge only after the final executable gate passes.

## Non-goals

- Fully normalizing every metadata field into relational columns.
- Replacing NFO or per-media sidecar metadata.
- UI redesign.
- Changing the intentional highlight source deletion policy.

## Checkpoint log

- [x] Sprint 3 plan recorded.
- [ ] SQLite media catalog complete.
- [ ] Catalog writers converted.
- [ ] Integration/recovery tests complete.
- [ ] Final validation green.
- [ ] PR merged.
