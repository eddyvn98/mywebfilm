import json

import queue_worker
import runtime_db
import media_job_store


def use_temp_db(tmp_path, monkeypatch):
    db = tmp_path / "cinema_state.db"
    monkeypatch.setattr(runtime_db, "DB_PATH", str(db))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    return db


def test_media_queue_migrates_json_and_marks_inflight_interrupted(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    jobs = tmp_path / "media_jobs.json"
    jobs.write_text(json.dumps([
        {"path": "a.mp4", "name": "a.mp4", "type": "highlight", "status": "processing", "output": None, "error": None},
        {"path": "b.ts", "name": "b.ts", "type": "convert", "status": "pending", "output": None, "error": None},
        {"path": "c.mp4", "name": "c.mp4", "type": "highlight", "status": "completed", "output": "c_highlight.mp4", "error": None},
    ]), encoding="utf-8")
    monkeypatch.setattr(queue_worker, "JOBS_FILE", str(jobs))

    q = queue_worker.MediaQueue()

    assert [item["status"] for item in q.items] == ["failed", "failed", "completed"]
    assert q.items[0]["error"] == "Interrupted by application restart"
    assert q.items[1]["error"] == "Interrupted by application restart"
    assert media_job_store.load_media_jobs() == q.items


def test_clear_completed_removes_finished_rows_from_sqlite(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    jobs = tmp_path / "media_jobs.json"
    monkeypatch.setattr(queue_worker, "JOBS_FILE", str(jobs))

    q = queue_worker.MediaQueue()
    item = media_job_store.add_media_job("done.mp4", "done.mp4", "highlight")
    media_job_store.update_media_job(item["id"], status="completed", output="done_highlight.mp4", error="")
    item.update(status="completed", output="done_highlight.mp4", error="")
    q.items = [item]

    q.clear_completed()

    assert q.items == []
    assert media_job_store.load_media_jobs() == []
