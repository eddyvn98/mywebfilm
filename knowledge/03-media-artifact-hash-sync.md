# Path-Hash Media Artifacts + Sync

Tags: `ffmpeg`, `media`, `filesystem`, `caching`

## Concept
Store derived artifacts (thumbnail/preview) using a deterministic key (`hash(path)`), then remap artifacts on move/rename.

## When to use
- Filesystem-first media apps
- Derived files that should not alter originals

## When NOT to use
- Content-addressed storage already using file hash
- Systems with immutable object IDs

## Example
```python
file_hash = md5(video_path.encode()).hexdigest()
thumb = f".mycinema/thumbnails/{file_hash}.jpg"

def sync_artifacts(old_path, new_path):
    os.rename(old_thumb, new_thumb)
```

