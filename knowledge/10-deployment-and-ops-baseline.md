# Deployment and Ops Baseline

Tags: `devops`, `deployment`, `testing`, `security`

## Concept
Keep local deployment simple but enforce minimum operational guardrails.

## When to use
- Self-hosted tools
- Small team/internal product

## When NOT to use
- Regulated production systems without CI/CD and secrets management

## Baseline Checklist
- Verify `ffmpeg` and `ffprobe` availability
- Keep `config.json` explicit and version-safe
- Add smoke tests for route registration and core processing
- Gate integration tests via env flags
- Remove hardcoded secrets from code

## Example
```python
if not ff.check_ffmpeg_presence():
    print("WARNING: ffmpeg not found")
```

