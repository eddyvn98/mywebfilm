"""Constrain AI metadata-driven media renames to one file in the source directory.

The metadata code/title are user- or model-controlled. A filename is *not*
trusted merely because the original media path was checked.
"""
import ntpath
import os
import re


_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_UNSAFE_TITLE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def plan_ai_media_rename(source_path, metadata):
    """Return (filename, target_path) or raise ValueError for unsafe metadata.

    Only the caller can authorize target_path against configured media roots.
    """
    if not isinstance(source_path, str) or not isinstance(metadata, dict):
        raise ValueError("Invalid media rename arguments")

    code = metadata.get("code") or ""
    title = metadata.get("title")
    if not isinstance(code, str) or (code and not _CODE_PATTERN.fullmatch(code)):
        raise ValueError("Invalid media code")
    if not isinstance(title, str):
        raise ValueError("Invalid media title")

    # Preserve names in Vietnamese/Japanese while removing Windows path syntax.
    clean_title = _UNSAFE_TITLE.sub("", title).strip(" .")
    clean_title = clean_title[:160].rstrip(" .")
    if not clean_title:
        raise ValueError("Invalid media title")

    ext = os.path.splitext(source_path)[1]
    filename = (f"[{code}] {clean_title}{ext}" if code else f"{clean_title}{ext}")
    if (len(filename) > 240
            or os.path.basename(filename) != filename
            or ntpath.basename(filename) != filename
            or _WINDOWS_DEVICE.match(filename)):
        raise ValueError("Invalid target filename")

    parent = os.path.dirname(source_path)
    target_path = os.path.join(parent, filename)
    # In addition to lexical checks, compare resolved directories to prevent
    # source-parent symlinks or path normalization from changing the destination.
    real_parent = os.path.normcase(os.path.realpath(parent))
    target_parent = os.path.normcase(os.path.realpath(os.path.dirname(target_path)))
    if real_parent != target_parent:
        raise ValueError("Target must remain in source directory")
    return filename, target_path
