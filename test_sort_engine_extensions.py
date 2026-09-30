from sort_engine import VIDEO_EXTS


def test_incoming_scan_supports_ts_media():
    assert ".ts" in VIDEO_EXTS
    assert ".m2ts" in VIDEO_EXTS
