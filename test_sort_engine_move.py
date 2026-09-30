import os

from sort_engine import SortEngine


def test_execute_move_uses_cross_drive_safe_move(monkeypatch, tmp_path):
    src = tmp_path / "source.mp4"
    dst = tmp_path / "nested" / "target.mp4"
    src.write_text("video")

    moved = {}

    def fake_move(source, target):
        moved["source"] = source
        moved["target"] = target
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.replace(source, target)
        return target

    def fail_rename(*args, **kwargs):
        raise AssertionError("execute_move must use shutil.move for cross-drive moves")

    monkeypatch.setattr("sort_engine.shutil.move", fake_move)
    monkeypatch.setattr("sort_engine.os.rename", fail_rename)

    engine = SortEngine(dry_run=False)
    plan = {"src": str(src), "studio_dst": str(dst), "filename": src.name}

    assert engine.execute_move(plan) is True
    assert moved == {"source": str(src), "target": str(dst)}
    assert dst.exists()


def test_run_does_not_report_failed_move(monkeypatch):
    engine = SortEngine(dry_run=False)
    video = {'path': 'D:/source.mp4', 'drive': 'D', 'filename': 'ABC-123.mp4', 'mtime': 0}
    plan = {
        'src': video['path'], 'studio_dst': 'G:/Sorted/ABC-123.mp4',
        'filename': video['filename'], 'pending': False, 'code': 'ABC-123', 'actresses': []
    }
    monkeypatch.setattr(engine, 'scan', lambda: [video])
    monkeypatch.setattr(engine, 'plan_move', lambda *args, **kwargs: plan)
    monkeypatch.setattr(engine, 'execute_move', lambda _plan: False)
    monkeypatch.setattr('sort_engine.save_cache', lambda _cache: None)

    state = engine.run()

    assert state['moved'] == []
