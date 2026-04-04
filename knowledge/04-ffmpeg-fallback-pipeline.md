# FFmpeg Multi-Stage Fallback

Tags: `ffmpeg`, `video`, `resilience`, `backend`

## Concept
Run a fast command first, then fallback to safer commands when media is malformed.

## When to use
- Mixed real-world media quality
- Thumbnail/preview jobs that must rarely fail

## When NOT to use
- Controlled media with strict encoding standards
- Latency-critical operations where fallback cost is unacceptable

## Example
```python
ok = run(fast_seek_cmd)
if not ok:
    ok = run(slow_seek_cmd)
if not ok:
    ok = run(no_seek_cmd)
```

