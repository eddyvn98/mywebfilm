# Production Hardening Sprint 2

Date: 2026-09-30
Baseline: `693771a2bec90e04d9ccb5e0774e3464d1ad5a62`

## Goal

Finish the reliability layer that was intentionally deferred from Sprint 1: transactional runtime state, crash-visible destructive operations, production serving, and startup diagnostics.

## Checkpoint 1 - SQLite runtime state

- Add a small built-in SQLite state layer with WAL and explicit transactions.
- Migrate history and favorites from legacy JSON on first use.
- Migrate media queue state from `data/media_jobs.json`.
- Preserve current API contracts so the frontend does not need a data-model rewrite.
- Add migration and concurrency regression tests.

## Checkpoint 2 - Operation journal

- Record delete, rename, and move operations before changing the filesystem.
- Advance operations through prepared / filesystem_done / completed / failed states.
- Expose incomplete operations through an authenticated diagnostics endpoint.
- Never silently discard post-filesystem metadata/cache failures.
- Add recovery-oriented tests.

## Checkpoint 3 - Production runtime

- Replace Flask's development server with Waitress for normal execution.
- Add startup checks for FFmpeg, FFprobe, writable data directory, and configured media roots.
- Extend the health endpoint with readiness diagnostics without leaking secrets.
- Keep tests/platform-neutral imports working.

## Checkpoint 4 - Release validation

- Run the existing regression suite plus new SQLite/journal tests.
- Run Python compile checks.
- Run JavaScript syntax checks.
- Use GitHub Actions when hosted runners are available; otherwise use the already-established isolated Railway fallback on the exact branch head.
- Merge only after the final head passes the executable test gate.

## Non-goals for this sprint

- Replacing `movies_cache.json` with a normalized media database.
- Redesigning metadata/NFO storage.
- UI feature work.
- Changing the intentional highlight policy that deletes the original only after validated success.

## Checkpoint log

- [x] Sprint 2 plan recorded.
- [ ] SQLite runtime state complete.
- [ ] Operation journal complete.
- [ ] Production runtime complete.
- [ ] Final test gate green.
- [ ] PR merged.
