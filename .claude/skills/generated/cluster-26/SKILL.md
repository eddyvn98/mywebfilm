---
name: cluster-26
description: "Skill for the Cluster_26 area of CinemaProject. 7 symbols across 2 files."
---

# Cluster_26

7 symbols | 2 files | Cohesion: 93%

## When to Use

- Understanding how save_jav_cache, extract_code, get_session work
- Modifying cluster_26-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `jav_metadata_service.py` | save_jav_cache, extract_code, get_session, fetch_jav_metadata, fetch_from_javlibrary (+1) |
| `category_service.py` | get_categories |

## Entry Points

Start here when exploring this area:

- **`save_jav_cache`** (Function) — `jav_metadata_service.py:20`
- **`extract_code`** (Function) — `jav_metadata_service.py:32`
- **`get_session`** (Function) — `jav_metadata_service.py:46`
- **`fetch_jav_metadata`** (Function) — `jav_metadata_service.py:54`
- **`fetch_from_javlibrary`** (Function) — `jav_metadata_service.py:79`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `save_jav_cache` | Function | `jav_metadata_service.py` | 20 |
| `extract_code` | Function | `jav_metadata_service.py` | 32 |
| `get_session` | Function | `jav_metadata_service.py` | 46 |
| `fetch_jav_metadata` | Function | `jav_metadata_service.py` | 54 |
| `fetch_from_javlibrary` | Function | `jav_metadata_service.py` | 79 |
| `fetch_from_javbus` | Function | `jav_metadata_service.py` | 113 |
| `get_categories` | Function | `category_service.py` | 18 |

## How to Explore

1. `gitnexus_context({name: "save_jav_cache"})` — see callers and callees
2. `gitnexus_query({query: "cluster_26"})` — find related execution flows
3. Read key files listed above for implementation details
