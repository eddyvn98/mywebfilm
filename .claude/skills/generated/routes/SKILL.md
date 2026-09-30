---
name: routes
description: "Skill for the Routes area of CinemaProject. 86 symbols across 23 files."
---

# Routes

86 symbols | 23 files | Cohesion: 84%

## When to Use

- Working with code in `routes/`
- Understanding how extract_search_intent, score_video, semantic_search work
- Modifying routes-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `llm_service.py` | call_gemini_api, call_local_llm, get_studio_by_code, clean_context, sanitize_metadata (+3) |
| `config_manager.py` | load_cache, save_cache, load_config, save_config, load_history (+3) |
| `ffmpeg_service.py` | get_best_gpu_encoder, process_highlight_video, remux_ts_to_mp4, convert_ts_to_mp4, get_video_duration (+2) |
| `routes/api_config.py` | get_config, update_config, add_folder, remove_folder, scan (+1) |
| `routes/api_auth.py` | get_origin, register_verify, login_options, login_verify, is_token_valid (+1) |
| `routes/api_ai.py` | ai_analyze, ai_chat_endpoint, get_unverified, ai_inject, ai_search |
| `security_service.py` | _save_credentials, verify_registration, get_authentication_options, verify_authentication, get_registration_options |
| `utils.py` | sync_artifacts, get_hash, get_metadata_paths, ensure_metadata_dirs |
| `routes/api_video.py` | get_videos, update_views, get_thumb, get_prev |
| `queue_worker.py` | _worker_loop, add_items, ensure_worker_started, get_status |

## Entry Points

Start here when exploring this area:

- **`extract_search_intent`** (Function) — `search_service.py:6`
- **`score_video`** (Function) — `search_service.py:140`
- **`semantic_search`** (Function) — `search_service.py:191`
- **`call_gemini_api`** (Function) — `llm_service.py:18`
- **`call_local_llm`** (Function) — `llm_service.py:57`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `extract_search_intent` | Function | `search_service.py` | 6 |
| `score_video` | Function | `search_service.py` | 140 |
| `semantic_search` | Function | `search_service.py` | 191 |
| `call_gemini_api` | Function | `llm_service.py` | 18 |
| `call_local_llm` | Function | `llm_service.py` | 57 |
| `get_studio_by_code` | Function | `llm_service.py` | 77 |
| `clean_context` | Function | `llm_service.py` | 84 |
| `sanitize_metadata` | Function | `llm_service.py` | 93 |
| `create_analyzer_prompt` | Function | `llm_service.py` | 124 |
| `parse_llm_json` | Function | `llm_service.py` | 164 |
| `normalize_metadata_with_llm` | Function | `llm_service.py` | 180 |
| `extract_search_intent` | Function | `llm_search_service.py` | 4 |
| `chat` | Function | `llm_agent_service.py` | 76 |
| `ai_analyze` | Function | `routes/api_ai.py` | 37 |
| `ai_chat_endpoint` | Function | `routes/api_ai.py` | 144 |
| `sync_artifacts` | Function | `utils.py` | 42 |
| `save_tags` | Function | `tag_service.py` | 23 |
| `add_tags` | Function | `tag_service.py` | 30 |
| `score_video` | Function | `llm_search_service.py` | 48 |
| `semantic_search` | Function | `llm_search_service.py` | 94 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Ai_search → Call_gemini_api` | cross_community | 5 |
| `Ai_inject → Get_studio_by_code` | cross_community | 4 |
| `Ai_inject → Clean_context` | cross_community | 4 |
| `Ai_inject → Call_gemini_api` | cross_community | 4 |
| `Scan → Get_hash` | cross_community | 4 |
| `Ai_search → Parse_llm_json` | cross_community | 4 |
| `Test_llm_pipeline → Get_studio_by_code` | cross_community | 4 |
| `Test_llm_pipeline → Clean_context` | cross_community | 4 |
| `Test_llm_pipeline → Call_gemini_api` | cross_community | 4 |
| `Ai_chat_endpoint → Call_gemini_api` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_26 | 1 calls |
| Cluster_5 | 1 calls |
| Cluster_21 | 1 calls |

## How to Explore

1. `gitnexus_context({name: "extract_search_intent"})` — see callers and callees
2. `gitnexus_query({query: "routes"})` — find related execution flows
3. Read key files listed above for implementation details
