import json
import threading

import runtime_db
import operation_journal


def use_temp_db(tmp_path, monkeypatch):
    db = tmp_path / "cinema_state.db"
    monkeypatch.setattr(runtime_db, "DB_PATH", str(db))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    return db


def test_list_state_migrates_legacy_json_once(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    legacy = tmp_path / "history_cache.json"
    legacy.write_text(json.dumps([{"full_path": "a.mp4"}]), encoding="utf-8")

    first = runtime_db.load_list_state("history", str(legacy))
    legacy.write_text(json.dumps([{"full_path": "changed.mp4"}]), encoding="utf-8")
    second = runtime_db.load_list_state("history", str(legacy))

    assert first == [{"full_path": "a.mp4"}]
    assert second == first


def test_transactional_list_mutation_preserves_concurrent_updates(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    errors = []

    def worker(index):
        try:
            runtime_db.mutate_list_state(
                "favorites",
                lambda items: items + [{"full_path": f"{index}.mp4"}],
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    items = runtime_db.load_list_state("favorites")
    assert {item["full_path"] for item in items} == {f"{i}.mp4" for i in range(20)}


def test_operation_journal_lists_non_completed_operations(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)

    pending = operation_journal.begin_operation("move", "a.mp4", "b.mp4")
    done = operation_journal.begin_operation("delete", "c.mp4")
    operation_journal.update_operation(done, "completed")
    operation_journal.update_operation(pending, "filesystem_done")

    incomplete = operation_journal.list_incomplete_operations()

    assert [row["id"] for row in incomplete] == [pending]
    assert incomplete[0]["status"] == "filesystem_done"
