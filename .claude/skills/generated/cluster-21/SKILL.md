---
name: cluster-21
description: "Skill for the Cluster_21 area of CinemaProject. 4 symbols across 2 files."
---

# Cluster_21

4 symbols | 2 files | Cohesion: 86%

## When to Use

- Understanding how save_nfo, get_ffmpeg_path, save_metadata_fast work
- Modifying cluster_21-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `metadata_injector.py` | get_ffmpeg_path, save_metadata_fast, inject_metadata |
| `nfo_service.py` | save_nfo |

## Entry Points

Start here when exploring this area:

- **`save_nfo`** (Function) — `nfo_service.py:52`
- **`get_ffmpeg_path`** (Function) — `metadata_injector.py:6`
- **`save_metadata_fast`** (Function) — `metadata_injector.py:17`
- **`inject_metadata`** (Function) — `metadata_injector.py:30`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `save_nfo` | Function | `nfo_service.py` | 52 |
| `get_ffmpeg_path` | Function | `metadata_injector.py` | 6 |
| `save_metadata_fast` | Function | `metadata_injector.py` | 17 |
| `inject_metadata` | Function | `metadata_injector.py` | 30 |

## How to Explore

1. `gitnexus_context({name: "save_nfo"})` — see callers and callees
2. `gitnexus_query({query: "cluster_21"})` — find related execution flows
3. Read key files listed above for implementation details
