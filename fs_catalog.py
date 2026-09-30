import ntpath
import os

import config_manager as cfg


def basename(path):
    return ntpath.basename(path) if "\\" in path else os.path.basename(path)


def dirname(path):
    return ntpath.dirname(path) if "\\" in path else os.path.dirname(path)


def join_path(parent, name):
    return ntpath.join(parent, name) if "\\" in parent else os.path.join(parent, name)


def delete_from_catalog(path):
    return cfg.mutate_cache(
        lambda items: [
            item for item in items
            if item.get("full_path") != path
        ]
    )


def rename_in_catalog(old_path, new_path, new_name):
    old_folder = basename(old_path)

    def update(items):
        for item in items:
            full_path = item.get("full_path", "")
            if full_path == old_path:
                item["full_path"] = new_path
                item["name"] = new_name
            elif full_path.startswith(old_path + os.sep) or full_path.startswith(old_path + "\\"):
                item["full_path"] = full_path.replace(old_path, new_path, 1)
                if item.get("folder") == old_folder:
                    item["folder"] = new_name
        return items

    return cfg.mutate_cache(update)


def move_in_catalog(moved_paths, target_dir):
    target_folder = basename(target_dir)

    def update(items):
        for item in items:
            full_path = item.get("full_path", "")
            for old_path, new_path in moved_paths:
                if full_path == old_path:
                    item["full_path"] = new_path
                    item["folder"] = target_folder
                    break
                if full_path.startswith(old_path + os.sep) or full_path.startswith(old_path + "\\"):
                    item["full_path"] = full_path.replace(old_path, new_path, 1)
                    break
        return items

    return cfg.mutate_cache(update)
