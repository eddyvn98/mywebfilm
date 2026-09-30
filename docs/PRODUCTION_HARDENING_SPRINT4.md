# Production Hardening Sprint 4

Date: 2026-09-30
Baseline: `0f3cc12e70ea8832cf50211a7d1d1aaeb82c90a0`

## Goal

Add recovery-grade backup/restore, failure-injection coverage, and a Windows-native end-to-end test suite so MyWebFilm can prove it survives realistic operational failures instead of only the happy path.

## Checkpoint 1 - Backup and restore

- Add SQLite-safe backup using the SQLite backup API instead of copying a live WAL database directly.
- Back up runtime credentials and local config/tag files alongside the database.
- Add manifest metadata and integrity verification.
- Restore into a staging directory first, validate the SQLite database, then atomically replace runtime state.
- Never overwrite the live database with an invalid or partial backup.
- Add backup retention cleanup.
- Add authenticated backup/restore diagnostics endpoints without exposing secret contents.

## Checkpoint 2 - Failure injection

- Simulate SQLite write failures, disk-full style write errors, permission failures, and locked-file failures.
- Verify filesystem operations leave operation-journal evidence when post-move catalog updates fail.
- Verify highlight/conversion failures keep the source.
- Verify backup failure never destroys the previous valid backup.
- Verify restore failure never replaces current runtime state.

## Checkpoint 3 - Windows E2E suite

- Add Windows-only tests for NT path construction, explorer launch command, os.startfile behavior, .bat launchers, and path authorization.
- Add optional real-FFmpeg tests gated by an environment variable.
- Add optional cross-drive move tests gated by configured Windows test roots.
- Keep the Windows suite safe by requiring disposable test directories.
- Add a dedicated Windows GitHub Actions job so it runs automatically whenever hosted runners are available again.

## Checkpoint 4 - Release validation

- Run import smoke and compileall.
- Run the full Linux/platform-neutral pytest suite with coverage.
- Run failure-injection tests.
- Validate modified/new core Python files remain below 300 lines.
- Attempt the Windows GitHub Actions job; if hosted runners still fail before allocation, record the external blocker and keep the suite ready.
- Merge only after the executable platform-neutral gate passes on the exact final head.

## Non-goals

- Rebuilding the UI.
- Changing the SQLite schema beyond recovery/backup metadata if needed.
- Requiring a permanent cloud deployment.
- Changing highlight deletion semantics.

## Checkpoint log

- [x] Sprint 4 plan recorded.
- [x] Backup/restore complete.
- [x] Failure injection complete.
- [x] Windows E2E suite complete — suite and `windows-latest` CI job are ready; GitHub still fails before runner allocation (`runner_id=0`, `steps=[]`).
- [x] Final validation green — code head `7b56e9e1e53fee6af9e81bb94ed8ad337ee2ee5f`: import smoke + compileall + 63 passed, 9 skipped, coverage 60.48%, `CI_FINAL_EXIT=0`.
- [x] PR merged — squash merge `2f1ba884e43989d58c7bf5f21bac983769674cec`.


## Validation note

The platform-neutral and failure-injection gate ran on the isolated Railway validator. Windows-specific tests were collected and skipped on Linux by design. GitHub Actions accepted both the Linux and `windows-latest` jobs, but both failed before any step executed with `runner_id=0` and empty step lists. This is the same external runner-provisioning condition documented in prior sprints, not a Windows test failure.

Failure injection found and fixed a real data-loss risk in MP4 re-encoding: the old swap sequence deleted the original before renaming the new file. The hardened path now uses `os.replace()` so a locked/failed replacement leaves the original intact.
