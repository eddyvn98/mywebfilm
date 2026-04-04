# Layered Flask Architecture

Tags: `flask`, `api`, `backend`, `modular`

## Concept
Split HTTP routes from business logic:
- `routes/*` for request/response
- `services/*` (or root services) for domain logic
- `config_manager` for persistence

## When to use
- Medium Flask apps with growing endpoints
- Teams needing clear ownership boundaries

## When NOT to use
- Tiny scripts (1-2 endpoints)
- Systems needing strict DDD/microservices from day one

## Example
```python
# routes/api_video.py
@video_bp.route('/api/videos')
def get_videos():
    return jsonify(cfg.load_cache())
```

