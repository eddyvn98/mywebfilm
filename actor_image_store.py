"""Private actor-photo storage and one-time migration from legacy static assets.

Actor names come from scraped metadata; never treat them as filesystem paths.
"""
import filecmp
import logging
import os
import re
import shutil
import tempfile
import unicodedata

from web_security import BASE_DIR, DATA_DIR

logger = logging.getLogger(__name__)
_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
}


def actor_image_dir():
    return os.path.abspath(os.path.join(DATA_DIR, "actors"))


def actor_image_filename(name):
    """Return a portable, Unicode-preserving JPEG filename (never a path)."""
    if not isinstance(name, str):
        raise ValueError("Invalid actor name")
    name = unicodedata.normalize("NFKC", name).strip()
    if not name or "/" in name or "\\" in name:
        raise ValueError("Invalid actor name")
    if name.lower().endswith(".jpg"):
        name = name[:-4]
    name = re.sub(r"\s+", "_", name)
    name = _INVALID_WINDOWS_CHARS.sub("_", name)
    name = name[:80].strip(" .")
    if not name or name.upper().split(".")[0] in _RESERVED_WINDOWS_NAMES:
        raise ValueError("Invalid actor name")
    return name + ".jpg"


def actor_image_path(name):
    root = os.path.realpath(actor_image_dir())
    target = os.path.realpath(os.path.join(root, actor_image_filename(name)))
    if os.path.commonpath([root, target]) != root:
        raise ValueError("Actor image path escapes private storage")
    return target


def migrate_legacy_actor_images():
    """Idempotently move old photos out of Flask's public static directory.

    Never delete the source until a complete private copy has been installed.
    Conflicting files remain untouched and are logged for manual resolution.
    """
    legacy = os.path.join(BASE_DIR, "static", "img", "actors")
    if not os.path.isdir(legacy):
        return 0
    destination = actor_image_dir()
    os.makedirs(destination, exist_ok=True)
    moved = 0
    for entry in os.scandir(legacy):
        if not entry.is_file(follow_symlinks=False) or not entry.name.lower().endswith(".jpg"):
            continue
        try:
            target = actor_image_path(entry.name)
            if os.path.lexists(target):
                if (not os.path.islink(target)
                        and os.path.isfile(target)
                        and filecmp.cmp(entry.path, target, shallow=False)):
                    os.unlink(entry.path)
                else:
                    logger.warning("actor_image_migration_conflict filename=%r", entry.name)
                continue
            fd, staged = tempfile.mkstemp(prefix=".actor-migrate-", dir=destination)
            try:
                with os.fdopen(fd, "wb") as output, open(entry.path, "rb") as source:
                    shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(staged, target)
            finally:
                if os.path.exists(staged):
                    os.unlink(staged)
            os.unlink(entry.path)
            moved += 1
        except (OSError, ValueError):
            logger.exception("actor_image_migration_failed filename=%r", entry.name)
    return moved
