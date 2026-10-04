# Automatic Metadata Pipeline - Deploy Checklist

This branch is prepared up to, but not including, deployment.

## What it does

- Detects recognizable movie codes from filenames.
- Queues metadata lookups automatically after a library scan.
- Keeps metadata jobs in SQLite so retries survive application restarts.
- Uses Javinizer CLI with the free r18dev scraper as the primary source.
- Falls back to the project's existing web metadata scrapers when needed.
- Validates that returned metadata matches the requested movie code.
- Stores source URL, source name, release date, runtime, studio, series, cast, genres and fetched timestamp.
- Writes an NFO sidecar after a verified match.
- Searches title, code, actor, genre, studio and series in the web UI.
- Sorts by views, actual file duration, release date and metadata update time.

## Required software on the Windows host

Existing requirements still apply:

- Python 3.12
- FFmpeg / FFprobe
- project Python dependencies

Add Javinizer Go before deployment.

Recommended Windows install:

```powershell
irm https://raw.githubusercontent.com/javinizer/javinizer-go/main/scripts/install.ps1 | iex
javinizer init
javinizer scrape IPX-535 --scrapers r18dev --output json
```

The final command is only a smoke test. It should print one JSON document.

## Runtime configuration

Defaults require no extra config when `javinizer` is on PATH.

Optional environment variables:

```text
CINEMA_JAVINIZER_BIN=javinizer
CINEMA_JAVINIZER_CONFIG=
CINEMA_JAVINIZER_TIMEOUT_SECONDS=60
CINEMA_METADATA_MONITOR_SECONDS=60
```

If Javinizer is installed outside PATH, set `CINEMA_JAVINIZER_BIN` to its executable path.

## First run after deployment

1. Back up `data/`, `config.json`, `tags.json`, and existing NFO files.
2. Install and initialize Javinizer.
3. Start MyWebFilm normally.
4. Run one library scan from the UI.
5. Check `GET /api/metadata/status`.
6. Confirm pending jobs gradually become completed.
7. Search by a known code, actor, studio or genre.
8. Verify metadata source fields in `GET /api/videos`.

No manual per-movie command is required. New coded files are queued after scans, and the metadata monitor also rechecks the catalog periodically.

## Deployment stop point

Do not merge/deploy until CI is green and the Windows host passes the Javinizer smoke test above.
