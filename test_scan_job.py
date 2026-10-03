import threading

from scan_job import ScanManager


def test_scan_manager_runs_in_background_and_completes():
    release = threading.Event()
    entered = threading.Event()

    def fake_scan(video_dirs):
        assert video_dirs == ["A", "B"]
        entered.set()
        release.wait(timeout=2)
        return [1, 2, 3]

    manager = ScanManager(scan_func=fake_scan)
    started, state = manager.start(["A", "B"])

    assert started is True
    assert state["status"] == "running"
    assert entered.wait(timeout=1)
    assert manager.status()["status"] == "running"

    second_started, second_state = manager.start(["A"])
    assert second_started is False
    assert second_state["status"] == "running"

    release.set()
    manager._thread.join(timeout=2)

    final = manager.status()
    assert final["status"] == "done"
    assert final["result_count"] == 3
    assert final["finished_at"] is not None


def test_scan_manager_records_failure():
    def fake_scan(_video_dirs):
        raise RuntimeError("boom")

    manager = ScanManager(scan_func=fake_scan)
    started, _ = manager.start(["A"])
    assert started is True

    manager._thread.join(timeout=2)
    final = manager.status()

    assert final["status"] == "failed"
    assert "boom" in final["error"]
