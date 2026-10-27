import hashlib
import os
from constants import METADATA_DIR_NAME


def get_hash(p):
    return hashlib.md5(p.encode()).hexdigest()


def get_metadata_paths(video_path):
    video_dir = os.path.dirname(video_path)
    file_hash = get_hash(video_path)
    meta_root = os.path.join(video_dir, METADATA_DIR_NAME)
    thumb_dir = os.path.join(meta_root, "thumbnails")
    prev_dir = os.path.join(meta_root, "previews")
    return {
        "root": meta_root,
        "thumb_dir": thumb_dir,
        "prev_dir": prev_dir,
        "thumb_path": os.path.join(
            thumb_dir,
            f"{file_hash}.jpg",
        ),
        "prev_path": os.path.join(
            prev_dir,
            f"{file_hash}.mp4",
        ),
    }


def ensure_metadata_dirs(paths):
    os.makedirs(
        paths["thumb_dir"],
        exist_ok=True,
    )
    os.makedirs(
        paths["prev_dir"],
        exist_ok=True,
    )


def sync_artifacts(old_path, new_path):
    try:
        old_hash = get_hash(old_path)
        new_hash = get_hash(new_path)
        if old_hash == new_hash:
            return

        old_dir = os.path.dirname(old_path)
        old_meta_root = os.path.join(
            old_dir,
            METADATA_DIR_NAME,
        )
        new_dir = os.path.dirname(new_path)
        new_meta_root = os.path.join(
            new_dir,
            METADATA_DIR_NAME,
        )

        thumb_new_dir = os.path.join(
            new_meta_root,
            "thumbnails",
        )
        prev_new_dir = os.path.join(
            new_meta_root,
            "previews",
        )
        os.makedirs(
            thumb_new_dir,
            exist_ok=True,
        )
        os.makedirs(
            prev_new_dir,
            exist_ok=True,
        )

        thumb_old = os.path.join(
            old_meta_root,
            "thumbnails",
            f"{old_hash}.jpg",
        )
        thumb_new = os.path.join(
            thumb_new_dir,
            f"{new_hash}.jpg",
        )
        legacy_thumb = os.path.join(
            old_dir,
            f"{old_hash}.jpg",
        )

        if os.path.exists(thumb_old):
            if not os.path.exists(thumb_new):
                os.rename(
                    thumb_old,
                    thumb_new,
                )
        elif os.path.exists(legacy_thumb):
            if not os.path.exists(thumb_new):
                os.rename(
                    legacy_thumb,
                    thumb_new,
                )

        prev_old = os.path.join(
            old_meta_root,
            "previews",
            f"{old_hash}.mp4",
        )
        prev_new = os.path.join(
            prev_new_dir,
            f"{new_hash}.mp4",
        )
        if (
            os.path.exists(prev_old)
            and not os.path.exists(prev_new)
        ):
            os.rename(
                prev_old,
                prev_new,
            )
        return True
    except Exception as e:
        print(
            f"Sync Artifact Error ({old_path} -> {new_path}): {e}"
        )
        return False


def _normalized_real(path):
    return os.path.normcase(
        os.path.realpath(
            os.path.abspath(str(path))
        )
    )


def _path_inside(path, roots):
    try:
        abs_path = _normalized_real(path)
    except Exception:
        return False

    for root in roots or []:
        if not root:
            continue
        try:
            abs_root = _normalized_real(root)
            common = os.path.commonpath(
                [abs_path, abs_root]
            )
            if (
                os.path.normcase(common)
                == os.path.normcase(abs_root)
            ):
                return True
        except (OSError, ValueError):
            continue
    return False


def trusted_media_roots(config=None):
    import config_manager as cfg

    configured = config or cfg.load_config()
    env_value = os.environ.get(
        "CINEMA_MEDIA_ROOTS",
        "",
    ).strip()
    if env_value:
        roots = [
            item.strip()
            for item in env_value.split(os.pathsep)
            if item.strip()
        ]
    else:
        # Backward-compatible safe default: current library roots
        # are trusted, but the web UI cannot expand beyond them.
        roots = list(
            configured.get("video_dirs", [])
        )

    seen = set()
    result = []
    for root in roots:
        try:
            normalized = _normalized_real(root)
        except Exception:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(root)
    return result


def check_media_root_allowed(path, config=None):
    if not path:
        return False
    return _path_inside(
        path,
        trusted_media_roots(config),
    )


def check_path_safe(
    path,
    allow_project_assets=False,
):
    if not path:
        return False
    try:
        import config_manager as cfg

        config = cfg.load_config()
        library_dirs = list(
            config.get("video_dirs", [])
        )

        # If CINEMA_MEDIA_ROOTS is set, every library path must
        # additionally stay inside those owner-configured roots.
        env_roots = os.environ.get(
            "CINEMA_MEDIA_ROOTS",
            "",
        ).strip()
        if env_roots and not _path_inside(
            path,
            trusted_media_roots(config),
        ):
            return False

        if _path_inside(
            path,
            library_dirs,
        ):
            return True

        if allow_project_assets:
            project_root = os.path.dirname(
                os.path.abspath(__file__)
            )
            static_root = os.path.join(
                project_root,
                "static",
            )
            return _path_inside(
                path,
                [static_root],
            )

        return False
    except Exception:
        return False
