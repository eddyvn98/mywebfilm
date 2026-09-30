from sort_engine import pick_destination_drive


def test_pick_destination_drive_uses_priority_order(monkeypatch):
    drive_map = {}

    monkeypatch.setattr("sort_engine.os.path.isdir", lambda path: True)
    monkeypatch.setattr("sort_engine.drive_free_ratio", lambda letter: {"G": 0.42, "H": 0.31, "E": 0.22}[letter])
    monkeypatch.setattr("sort_engine.save_drive_map", lambda data: None)

    first = pick_destination_drive("JAV/Others_Q_T", drive_map)
    second = pick_destination_drive("JAV/Others_Q_T", drive_map)
    third = pick_destination_drive("JAV/Studio_A", drive_map)

    assert first == "G"
    assert second == "G"
    assert third == "G"


def test_pick_destination_drive_falls_back_when_g_full(monkeypatch):
    drive_map = {}

    monkeypatch.setattr("sort_engine.os.path.isdir", lambda path: True)
    monkeypatch.setattr("sort_engine.drive_free_ratio", lambda letter: {"G": 0.09, "H": 0.18, "E": 0.27}[letter])
    monkeypatch.setattr("sort_engine.save_drive_map", lambda data: None)

    assert pick_destination_drive("JAV/Others_Q_T", drive_map) == "H"
