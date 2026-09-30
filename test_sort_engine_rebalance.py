from sort_engine import SortEngine


def test_rebalance_uses_fresh_drive_map_and_processes_sorted_library(monkeypatch):
    engine = SortEngine(dry_run=False)
    engine.drive_map = {"JAV/DASD": "E"}

    files = [
        {"path": r"G:\Sorted_Videos\JAV\DASD\DASD-001.mp4", "drive": "G", "filename": "DASD-001.mp4", "mtime": 0},
        {"path": r"H:\Sorted_Videos\JAV\DASD\DASD-002.mp4", "drive": "H", "filename": "DASD-002.mp4", "mtime": 0},
        {"path": r"E:\Sorted_Videos\JAV\DASD\DASD-003.mp4", "drive": "E", "filename": "DASD-003.mp4", "mtime": 0},
    ]

    monkeypatch.setattr(engine, "scan_sorted_library", lambda: files, raising=False)
    monkeypatch.setattr(engine, "lookup_actress", lambda code: ["Test Actress"])

    seen_drive_maps = []

    def fake_pick_destination_drive(group_key, drive_map):
        seen_drive_maps.append(dict(drive_map))
        return ["G", "H", "E"][len(seen_drive_maps) - 1]

    monkeypatch.setattr("sort_engine.pick_destination_drive", fake_pick_destination_drive)

    moved = []

    def fake_execute_move(plan):
        moved.append(plan["studio_dst"])
        return True

    monkeypatch.setattr(engine, "execute_move", fake_execute_move)

    state = engine.rebalance()

    assert seen_drive_maps[0] == {}
    assert moved == [
        r"G:\Sorted_Videos\JAV\Others_A_D\DASD-001.mp4",
        r"H:\Sorted_Videos\JAV\Others_A_D\DASD-002.mp4",
        r"E:\Sorted_Videos\JAV\Others_A_D\DASD-003.mp4",
    ]
    assert state["status"] == "done"
