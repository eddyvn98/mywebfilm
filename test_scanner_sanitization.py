import os
import scanner_service


def test_excluded_directories_pruning(tmp_path, monkeypatch):
    root = str(tmp_path)
    dirs = [".cache", ".gradle", "node_modules", "$recycle.bin", "ValidFolder"]
    files = ["sample.mp4"]

    def fake_walk(_path):
        yield root, dirs, files

    monkeypatch.setattr(scanner_service.os, "walk", fake_walk)

    # Calling the iterator will prune dirs in-place
    list(scanner_service._iter_media_files([root]))

    assert dirs == ["ValidFolder"]


def test_typescript_files_rejected(tmp_path):
    # .d.ts should always be rejected
    dts_file = tmp_path / "index.d.ts"
    dts_file.write_text("export interface Foo {}", encoding="utf-8")
    assert scanner_service.is_valid_media_file(str(dts_file), "index.d.ts", is_video=True) is False

    # Plain text .ts file should be rejected
    ts_file = tmp_path / "app.ts"
    ts_file.write_text("console.log('hello');", encoding="utf-8")
    assert scanner_service.is_valid_media_file(str(ts_file), "app.ts", is_video=True) is False

    # Real MPEG-TS starting with 0x47 and > 100KB should be accepted
    real_ts = tmp_path / "valid.ts"
    real_ts.write_bytes(b"\x47" + b"\x00" * (120 * 1024))
    assert scanner_service.is_valid_media_file(str(real_ts), "valid.ts", is_video=True) is True


def test_corrupted_empty_video_stub_detection(tmp_path):
    # 48-byte corrupted MP4 stub with empty mdat
    stub_48 = (
        b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41\x00\x00\x00\x08free\x00\x00\x00\x00mdat"
    )
    stub_file = tmp_path / "corrupted_highlight.mp4"
    stub_file.write_bytes(stub_48)

    assert scanner_service.is_corrupted_empty_video(str(stub_file), len(stub_48)) is True
    assert (
        scanner_service.is_valid_media_file(
            str(stub_file), "corrupted_highlight.mp4", is_video=True
        )
        is False
    )


def test_image_filtering(tmp_path):
    # Android 9-patch should be rejected
    nine_patch = tmp_path / "btn.9.png"
    nine_patch.write_bytes(b"dummy")
    assert scanner_service.is_valid_media_file(str(nine_patch), "btn.9.png", is_video=False) is False

    # Poster/cover artwork should be rejected from appearing as individual media cards
    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"dummy-image")
    assert scanner_service.is_valid_media_file(str(poster), "poster.jpg", is_video=False) is False

    # Tiny icons (<30KB) should be rejected
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"x" * 1024)
    assert scanner_service.is_valid_media_file(str(icon), "icon.png", is_video=False) is False
