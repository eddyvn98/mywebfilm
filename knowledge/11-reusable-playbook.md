# Reusable Playbook: Local-First Media Library Web App

## 1) Step-by-Step Workflow (From Scratch)

1. Define scope
- Inputs: local media folders
- Outputs: browse/search/play, previews, metadata, history/favorites
- Constraints: single machine, no DB, fast startup

2. Initialize project structure
- `routes/` for API endpoints
- `services/` for processing logic
- `static/` + `templates/` for UI
- `data/` (or root JSON files) for config/cache/history/favorites

3. Implement config + persistence layer first
- Add JSON load/save utilities with mtime memory cache
- Create defaults for all configs
- Add schema-safe merge (`defaults + file_values`)

4. Build core scan pipeline
- Recursively scan configured roots
- Normalize items (`name`, `path`, `type`, `size`, `mtime`, `date_added`)
- Persist to cache
- Preserve old metadata/views when rescanning

5. Add derived media pipeline
- Thumbnail endpoint (lazy-generate + store)
- Preview endpoint (lazy-generate + store)
- Sidecar artifact folder (e.g. `.appmeta/thumbnails`, `.appmeta/previews`)

6. Add async processing queue
- Queue API: add/status/clear
- Background worker thread
- Task types: convert/highlight/etc.
- Update cache after successful task

7. Add file operations with consistency
- Delete / rename / move / mkdir
- Always sync cache + artifacts after path changes

8. Add security/auth
- Session auth for local UI
- WebAuthn support for strong login
- Optional one-time token gate for remote tunnel

9. Build frontend orchestration
- Central state object
- API wrapper module
- Grid rendering + filters + sort + pagination/infinite scroll
- Persist essential UI state in `localStorage`

10. Add tests + operational checks
- Smoke tests for route registration
- Unit tests for conversion/selection logic
- Integration tests behind env flag
- Startup check for ffmpeg/ffprobe presence

11. Add run/deploy scripts
- Local run script
- Optional tunnel setup script
- One-page operator README

---

## 2) Decision Tree (If X -> Do Y)

- If data size is small/medium and single-host -> use JSON files + mtime caching  
- If data size grows or multi-user concurrency appears -> migrate persistence to SQLite/Postgres

- If media jobs block HTTP requests -> add background queue worker  
- If jobs exceed single-machine thread model -> move to external worker system (RQ/Celery)

- If ffmpeg fails on edge files -> add staged fallback commands (fast seek -> slow seek -> no seek)

- If files are frequently moved/renamed -> use deterministic artifact key + artifact sync utility  
- If stable file identity is required across moves -> switch keying from `path-hash` to `content-hash/UUID`

- If remote access is needed quickly -> tunnel + one-time token + WebAuthn  
- If production internet deployment -> proper reverse proxy + TLS + secret management + RBAC

- If UI slows with large grids -> page/infinite-scroll + lazy media loading  
- If search/filter complexity increases -> move filtering/sorting server-side

- If AI enrichment is optional/unreliable -> keep deterministic regex/rule fallback always enabled

---

## 3) Common Pitfalls

- Hardcoded secrets (`secret_key`, admin IDs, tokens) in source
- Cache/data drift after move/rename/convert operations
- Path-based artifact keys without sync on rename
- Blocking ffmpeg execution in request thread
- Over-concurrent ffmpeg causing CPU/RAM thrash
- Missing fallback logic for malformed/short media
- Mixing many debug scripts into production root
- Encoding/locale issues in logs (non-UTF8 environments)
- No startup dependency checks (`ffmpeg`, `ffprobe`)
- No test gating for external integrations (AI/web scraping)

---

## 4) Default Configs (Safe Baseline)

```json
{
  "video_dirs": [],
  "auto_convert_ts": false,
  "preferred_codec": "h264",
  "llm_enabled": false,
  "llm_provider": "gemini",
  "llm_api_key": "",
  "thumbnail": {
    "seek_time": "00:00:05",
    "size": "300:450"
  },
  "preview": {
    "seek_time": "00:00:10",
    "duration_sec": 3,
    "size": "240:360"
  },
  "processing": {
    "ffmpeg_max_concurrency": 2
  },
  "cache": {
    "items_file": "movies_cache.json",
    "history_file": "history_cache.json",
    "favorites_file": "favorites_cache.json"
  },
  "security": {
    "require_auth": true,
    "allow_localhost_bootstrap": true,
    "remote_one_time_token": true
  }
}
```

---

## 5) Best Practices (Reusable Defaults)

- Keep strict module boundaries: route layer must stay thin
- Wrap all external tool calls with retries/fallbacks + explicit error messages
- Use idempotent cache updates after each filesystem mutation
- Limit heavy subprocess concurrency with semaphore
- Prefer lazy generation for thumbnails/previews instead of upfront batch processing
- Always include deterministic fallback path when AI/search fails
- Track metadata version/timestamp per item for future migrations
- Keep operational scripts separate (`scripts/`, `ops/`)
- Add a single health endpoint checking core dependencies and writable paths
- Ship with a “minimum viable test suite”:
1. API routes load
2. scanner returns stable schema
3. queue transitions status correctly
4. file rename/move keeps artifacts and cache consistent

---

## 6) Copy-Paste Execution Checklist

1. Create folder structure and config manager  
2. Implement scanner + cache schema  
3. Implement stream/thumbnail/preview endpoints  
4. Add queue worker + process endpoints  
5. Add FS operations + artifact sync  
6. Add auth (session + optional WebAuthn/token)  
7. Build frontend state/API/grid modules  
8. Add tests (smoke/unit/integration-gated)  
9. Add run/tunnel scripts + dependency checks  
10. Freeze defaults and document operator flow

