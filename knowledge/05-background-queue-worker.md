# Background Queue Worker (Thread + Status API)

Tags: `queue`, `async`, `flask`, `processing`

## Concept
Offload long-running processing into a worker thread; expose queue status via API polling.

## When to use
- CPU-heavy jobs in sync web apps
- Need simple async without Celery/Redis

## When NOT to use
- Horizontal scaling with many workers
- Exactly-once guarantees required

## Example
```python
media_queue.add_items(paths, task_type="convert")

@process_bp.route('/api/process/status')
def status():
    return jsonify(media_queue.get_status())
```

