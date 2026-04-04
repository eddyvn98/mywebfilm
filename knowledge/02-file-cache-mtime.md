# File Cache With mtime Guard

Tags: `cache`, `json`, `python`, `performance`

## Concept
Load JSON once, then reload only if file modification time changes.

## When to use
- Single-node apps
- JSON-backed state/config
- Read-heavy workloads

## When NOT to use
- Multi-node distributed systems
- Strong consistency requirements

## Example
```python
if _config_cache is not None and current_mtime <= _config_mtime:
    return _config_cache
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    _config_cache = json.load(f)
```

