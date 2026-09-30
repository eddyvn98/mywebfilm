from scanner_service import _normalize_roots


def test_normalize_roots_adds_sorted_drives_and_dedupes():
    roots = _normalize_roots([
        "E:\\",
        "E:\\Processed",
        "E:\\Sorted_Videos",
        "E:\\",
    ])

    assert "G:\\Sorted_Videos" in roots
    assert "H:\\Sorted_Videos" in roots
    assert "E:\\Sorted_Videos" not in roots
    assert roots.count("E:\\") == 1
    assert roots.count("E:\\Processed") == 0
