import json

import queue_worker


def test_media_queue_marks_inflight_jobs_interrupted_on_restart(tmp_path, monkeypatch):
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

    persisted = json.loads(jobs.read_text(encoding="utf-8"))
    assert persisted[0]["status"] == "failed"
    assert persisted[1]["status"] == "failed"


def test_clear_completed_persists_empty_job_list(tmp_path, monkeypatch):
    jobs = tmp_path / "media_jobs.json"
    monkeypatch.setattr(queue_worker, "JOBS_FILE", str(jobs))
    q = queue_worker.MediaQueue()
    q.items = [{"path": "done.mp4", "type": "highlight", "status": "completed"}]

    q.clear_completed()

    assert q.items == []
    assert json.loads(jobs.read_text(encoding="utf-8")) == []
