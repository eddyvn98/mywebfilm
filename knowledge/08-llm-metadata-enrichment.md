# LLM Metadata Enrichment With Deterministic Fallback

Tags: `ai`, `llm`, `metadata`, `search`

## Concept
Combine web context + prompt constraints + strict JSON parsing; if LLM fails, fallback to regex/rules.

## When to use
- Semi-structured metadata extraction
- Imperfect external context sources

## When NOT to use
- High-assurance data pipelines needing deterministic outputs only
- Zero external dependency environments

## Example
```python
raw = call_local_llm(prompt)
data = parse_llm_json(raw)
if not data:
    data = {"code": regex_code(filename), "actors": []}
```

