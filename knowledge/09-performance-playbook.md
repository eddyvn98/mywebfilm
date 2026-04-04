# Performance Playbook (Filesystem Media App)

Tags: `performance`, `ffmpeg`, `io`, `python`

## Concept
Optimize around I/O and subprocess bottlenecks with practical controls.

## When to use
- Local media catalogs with thousands of files

## When NOT to use
- Apps already bottlenecked by remote DB/network latency

## Tactics
- Limit ffmpeg concurrency via semaphore
- Reuse cached metadata/views/date when rescanning
- Probe video duration only when missing
- Keep offline roots as sticky cache entries

## Example
```python
ffmpeg_semaphore = threading.Semaphore(2)
if duration <= 0:
    duration = ffmpeg_service.get_video_duration(fp)
```

