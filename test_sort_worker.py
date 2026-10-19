from datetime import datetime
import os
import time
from unittest.mock import MagicMock, patch

import pytest
import sort_worker


def test_is_file_ready_for_sort(tmp_path):
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"sample video bytes" * 100)

    mtime = os.stat(str(test_file)).st_mtime
    assert sort_worker.is_file_ready_for_sort(str(test_file), now=mtime) is False
    assert sort_worker.is_file_ready_for_sort(str(test_file), now=mtime + 30) is True
    assert sort_worker.is_file_ready_for_sort(str(tmp_path / "missing.mp4"), now=time.time()) is False


def test_seconds_until_daily_target():
    # If now is 02:00, target 04:00 is in 2 hours = 7200s
    dt_early = datetime(2026, 10, 11, 2, 0, 0)
    secs = sort_worker.seconds_until_daily_target(4, 0, now_dt=dt_early)
    assert secs == 7200

    # If now is 05:00, target 04:00 tomorrow is in 23 hours = 82800s
    dt_late = datetime(2026, 10, 11, 5, 0, 0)
    secs = sort_worker.seconds_until_daily_target(4, 0, now_dt=dt_late)
    assert secs == 23 * 3600


def test_daily_state_persistence(tmp_path, monkeypatch):
    state_file = str(tmp_path / "state.json")
    monkeypatch.setattr("sort_worker.STATE_FILE", state_file)

    assert sort_worker.get_last_daily_sort_date() is None
    sort_worker.set_last_daily_sort_date("2026-10-11")
    assert sort_worker.get_last_daily_sort_date() == "2026-10-11"


def test_run_auto_sort_cycle_no_files(monkeypatch):
    monkeypatch.setattr("sort_worker.collect_ready_incoming_files", lambda: [])
    mock_engine = MagicMock()
    monkeypatch.setattr("sort_worker.SortEngine", mock_engine)

    moved = sort_worker.run_auto_sort_cycle()
    assert moved == 0
    mock_engine.assert_not_called()


def test_run_auto_sort_cycle_with_files(monkeypatch, tmp_path):
    monkeypatch.setattr("sort_worker.STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr("sort_worker.collect_ready_incoming_files", lambda: ["E:/Incoming/video.mp4"])
    
    mock_engine_inst = MagicMock()
    mock_engine_inst.run.return_value = {
        "moved": [{"filename": "video.mp4"}],
        "pending_review": [],
        "errors": [],
    }
    monkeypatch.setattr("sort_worker.SortEngine", lambda dry_run=False: mock_engine_inst)
    
    refreshed = []
    monkeypatch.setattr("sort_worker._refresh_catalog_after_sort", lambda: refreshed.append(True))

    moved = sort_worker.run_auto_sort_cycle()
    assert moved == 1
    assert refreshed == [True]
    mock_engine_inst.run.assert_called_once()
    assert sort_worker.get_last_daily_sort_date() == datetime.now().strftime("%Y-%m-%d")


def test_start_and_stop_sort_service():
    sort_worker.start_sort_service()
    assert sort_worker._monitor_thread is not None
    assert sort_worker._monitor_thread.is_alive()

    sort_worker.stop_sort_service()
    sort_worker._monitor_thread.join(timeout=2)
    assert not sort_worker._monitor_thread.is_alive()
