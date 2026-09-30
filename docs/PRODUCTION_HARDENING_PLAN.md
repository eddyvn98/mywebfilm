# Production Hardening Plan

Date: 2026-09-30
Branch: `production-hardening-2026-09-30`
Baseline: `356f9ac4a65f9893439fd230220d8aa0985bdaa4`

## Goal

Move MyWebFilm from a personal app that works on the happy path to a production-ready personal media manager with explicit safety, reproducible setup, CI quality gates, recovery-friendly persistence, and hardened remote access.

The intended highlight behavior is preserved: a successful highlight job may delete the original source file to save storage. Production hardening must guarantee that deletion happens only after the generated highlight has been validated.

## Checkpoint 1 - Security boundary

- Remove the hard-coded Flask secret and load a strong secret from environment/runtime storage.
- Harden session cookies.
- Stop returning API keys/cookies from `/api/config`.
- Apply path authorization to every endpoint that accepts filesystem paths before reading, writing, moving, processing, or launching files.
- Restrict WebAuthn/proxy origin handling to an allowlisted host/origin model.
- Make remote tunnel tokens expiring and single-use for login.
- Add regression tests for the security boundary.

## Checkpoint 2 - Data and destructive-operation safety

- Make JSON persistence atomic with temp-write + fsync + replace.
- Preserve the product rule that highlight jobs delete source files after success.
- Validate generated highlights with ffprobe before deleting the source.
- Never report a sorter move as successful when the filesystem move failed.
- Add tests covering failure-before-delete and move failure behavior.

## Checkpoint 3 - Frontend injection hardening

- Centralize HTML/attribute escaping for dynamic values.
- Remove unsafe interpolation of filenames, paths, actors, genres, studios, and metadata where practical.
- Prefer data attributes/event listeners over inline JavaScript values for filesystem-derived strings.
- Add lightweight static regression tests for critical rendering helpers.

## Checkpoint 4 - Reproducible build and CI

- Add pinned Python dependency manifest.
- Add pytest configuration and coverage baseline.
- Add GitHub Actions CI for syntax/import checks, tests, and security-focused regression tests.
- Keep Windows-only runtime behavior mockable so CI can run on GitHub-hosted Linux runners.
- Document local setup and production launch expectations.

## Checkpoint 5 - Runtime state hygiene and operations

- Stop tracking authentication/runtime cache data in Git.
- Extend `.gitignore` for runtime state.
- Add a health endpoint with dependency/config status that does not expose secrets.
- Add structured application logging for high-value operations.
- Document backup/recovery expectations and known platform assumptions.
- Persist media-job state; mark in-flight jobs interrupted after restart instead of silently losing or auto-resuming them.

## Release gate

The pull request may merge only when:

1. CI exists and reports success on the final PR head.
2. Security regression tests pass.
3. Destructive highlight behavior is validated and source deletion remains intentional.
4. No committed runtime credential state remains.
5. The final diff is reviewed for accidental secret exposure.
6. The production hardening checklist in this document is updated to reflect completed work.

## Checkpoint log

- [x] Plan recorded.
- [x] Checkpoint 1 complete.
- [x] Checkpoint 2 complete.
- [x] Checkpoint 3 complete.
- [x] Checkpoint 4 complete.
- [x] Checkpoint 5 complete.
- [x] Fallback CI green — Railway checked out commit `926612916f1954d81be8522e8ed22588e5b77a94` from `production-hardening-2026-09-30`: 36 passed, 3 skipped, coverage 40.50%.
- [!] GitHub Actions remains unavailable at the runner-provisioning layer (`runner_id=0`, `steps=[]`) on Linux and Windows runner labels; this is recorded as an external CI infrastructure exception, not a test failure.
- [x] PR merged — squash merge `693771a2bec90e04d9ccb5e0774e3464d1ad5a62`.


## Release validation exception

GitHub-hosted Actions could not provision any runner for this private repository on 2026-09-30. Multiple runs across `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-slim`, and `windows-latest` failed before execution with `runner_id=0` and an empty step list.

To avoid merging untested code, the same hardening branch was connected to a temporary isolated Railway service and executed with the repository's pytest quality gate. The final code commit validated there was:

- Commit: `926612916f1954d81be8522e8ed22588e5b77a94`
- Result: 36 passed, 3 skipped
- Coverage: 40.50% (required minimum: 15%)
- External LLM integration tests remained intentionally skipped unless `RUN_LLM_INTEGRATION_TESTS=1`.

This fallback result is accepted for this release because GitHub Actions failed before any repository code or workflow step could execute.
