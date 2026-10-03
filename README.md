# MyWebFilm

Local-first Flask media library manager for Windows with streaming, metadata management, WebAuthn login, FFmpeg processing, and automatic sorting.

## Requirements

- Python 3.12 recommended.
- FFmpeg and FFprobe available on PATH.
- Windows is required for desktop-launch features such as Explorer/MPC-HC; the core test suite is platform-neutral.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python webfilm.py
```

Open `http://localhost:5000`.

Normal execution uses Waitress instead of Flask's development server. Optional runtime settings: `CINEMA_HOST` (default `127.0.0.1`), `CINEMA_PORT` (default `5000`), and `CINEMA_THREADS` (default `8`). For a Cloudflare Tunnel on the same Windows 11 PC, keep the app bound to `127.0.0.1`.

## Runtime data

Runtime authentication state and generated secrets live under `data/` by default and must not be committed. Set `CINEMA_DATA_DIR` to move that directory. The media catalog, history, favorites, media-job state, migration markers, and destructive-operation journal entries are stored in `data/cinema_state.db` (SQLite/WAL).

`CINEMA_SECRET_KEY` can be supplied explicitly. If omitted, the app creates a random persistent key in `data/flask_secret.key`.

For HTTPS/tunnel use, set `CINEMA_SECURE_COOKIES=1`.

Windows 11 performance knobs:
- `CINEMA_FFMPEG_CONCURRENCY` controls the shared FFmpeg process budget (default `2`; use `1` if the PC is also used interactively).
- `CINEMA_FFMPEG_SHORT_TIMEOUT_SECONDS` controls thumbnail/preview/startup command timeout (default `90`).
- `CINEMA_FFPROBE_TIMEOUT_SECONDS` controls probe timeout (default `30`).
- `CINEMA_FFMPEG_LONG_TIMEOUT_SECONDS` controls long conversion/highlight timeout (default `21600`, six hours).
- `CINEMA_CONFIG_DIR` can move `config.json` and legacy JSON migration files away from the repository. Paths are resolved absolutely, so Task Scheduler or other launchers no longer depend on their working directory.

`cloudflared.exe` is intentionally not stored in Git. Install Cloudflare Tunnel separately or place a local copy next to `setup_tunnel.py`; it is ignored by Git.

### Upgrade note

Older revisions tracked `credentials.json`, `history_cache.json`, and `favorites_cache.json`. The hardened version no longer tracks these files. WebAuthn credentials now live in `data/credentials.json`; if an old local `credentials.json` is still present on first run, it is migrated automatically. Legacy `movies_cache.json`, `history_cache.json`, `favorites_cache.json`, and `data/media_jobs.json` are imported into SQLite on first use when no corresponding SQLite state exists. Media-catalog migration is marked in SQLite so an old `movies_cache.json` cannot be silently re-imported after the catalog is later cleared. If Git has already removed the old WebAuthn credential file, register the device/passkey again from localhost.

Back up `data/` (especially `cinema_state.db` and `credentials.json`) plus your local `config.json`, `tags.json`, and media-sidecar `.nfo` files before major upgrades.

## Highlight behavior

Highlight processing intentionally replaces storage usage by deleting the original source after the generated highlight passes media validation. If FFmpeg or FFprobe validation fails, the source is retained.

## Tests

```bash
pytest -q
```

GitHub Actions runs Python compilation, pytest with coverage, security/data-safety regressions, and JavaScript syntax checks for pushes and pull requests.

## Production hardening

See `docs/PRODUCTION_HARDENING_PLAN.md`.


## Recovery diagnostics

Authenticated users can inspect incomplete or failed destructive filesystem operations at:

`GET /api/diagnostics/operations`

Delete, rename, and move operations are journaled before the filesystem changes. A response with `status: partial` means the filesystem change happened but a later metadata/artifact step needs attention. Keep the returned `operation_id` when troubleshooting.

`GET /api/health` reports FFmpeg/FFprobe availability, writable runtime storage, SQLite readiness, and media-root availability without returning configured filesystem paths or secrets.


## Media catalog concurrency

The catalog is stored as one SQLite row per media path. View increments update only the matching row inside an immediate transaction. Long scans replace the catalog transactionally and merge the latest view counts at commit time, preventing a scan from overwriting views recorded while the scan was running.

`POST /api/clear_cache` clears the SQLite media catalog and removes any legacy `movies_cache.json` so stale data cannot return on the next request.


## Backup and restore

Backups are stored under `data/backups/` by default. The location can be changed with `CINEMA_BACKUP_DIR`. Each backup contains a SQLite-consistent copy of `cinema_state.db`, any existing WebAuthn credentials, local config/tags, and a SHA-256 manifest.

Authenticated endpoints:

- `GET /api/backup` — list and verify backup sets.
- `POST /api/backup/create` — create a new backup.
- `POST /api/backup/verify` with `{"backup_id":"..."}` — integrity-check a backup.
- `POST /api/backup/restore` with `{"backup_id":"...","confirm":"RESTORE"}` — restore after validation.

Restore creates an emergency backup of the current state first. If restore fails midway, the emergency backup is automatically reapplied. A successful restore returns `restart_required: true`; restart the app so in-memory config, tags, credentials, and sessions are reloaded cleanly.

Set `CINEMA_BACKUP_KEEP` to control automatic retention; the default is 10 backups.

## Windows E2E

`test_windows_e2e.py` contains Windows-native checks for `os.startfile`, Explorer selection, Windows path authorization, and batch launchers.

Two destructive/real-resource tests are opt-in:

- `RUN_WINDOWS_FFMPEG_E2E=1` enables a real FFmpeg/FFprobe roundtrip.
- Set both `CINEMA_WINDOWS_TEST_ROOT_A` and `CINEMA_WINDOWS_TEST_ROOT_B` to disposable directories on different drives to enable the real cross-drive move test.

Never point the cross-drive variables at production media folders.
