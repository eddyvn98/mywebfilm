---
name: cluster-5
description: "Skill for the Cluster_5 area of CinemaProject. 6 symbols across 4 files."
---

# Cluster_5

6 symbols | 4 files | Cohesion: 77%

## When to Use

- Understanding how run_test, test_llm_pipeline, search_web work
- Modifying cluster_5-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `test_llm_pipeline.py` | _integration_enabled, test_llm_pipeline |
| `search_service.py` | search_web, search_jav_context |
| `test_metadata_quality.py` | run_test |
| `llm_agent_service.py` | _tool_web_search |

## Entry Points

Start here when exploring this area:

- **`run_test`** (Function) — `test_metadata_quality.py:5`
- **`test_llm_pipeline`** (Function) — `test_llm_pipeline.py:23`
- **`search_web`** (Function) — `search_service.py:55`
- **`search_jav_context`** (Function) — `search_service.py:91`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `run_test` | Function | `test_metadata_quality.py` | 5 |
| `test_llm_pipeline` | Function | `test_llm_pipeline.py` | 23 |
| `search_web` | Function | `search_service.py` | 55 |
| `search_jav_context` | Function | `search_service.py` | 91 |
| `_integration_enabled` | Function | `test_llm_pipeline.py` | 8 |
| `_tool_web_search` | Function | `llm_agent_service.py` | 16 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Test_llm_pipeline → Get_studio_by_code` | cross_community | 4 |
| `Test_llm_pipeline → Clean_context` | cross_community | 4 |
| `Test_llm_pipeline → Call_gemini_api` | cross_community | 4 |
| `Run_test → Get_studio_by_code` | cross_community | 4 |
| `Run_test → Clean_context` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Routes | 2 calls |

## How to Explore

1. `gitnexus_context({name: "run_test"})` — see callers and callees
2. `gitnexus_query({query: "cluster_5"})` — find related execution flows
3. Read key files listed above for implementation details
