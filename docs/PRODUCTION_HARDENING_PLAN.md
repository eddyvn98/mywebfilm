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
- [ ] CI green — blocked as of 2026-09-30 by GitHub-hosted runner provisioning failure (`runner_id=0`, `steps=[]`) before any workflow step starts.
- [ ] PR merged — intentionally held until CI is genuinely green.
