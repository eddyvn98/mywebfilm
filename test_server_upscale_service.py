"""Pure mock tests for GPU streamer: commands, access, limits and cleanup."""
import server_upscale_service as service
import pytest


class FakeProcess:
    def __init__(self):
        self.alive = True
    def poll(self):
        return None if self.alive else 0
    def terminate(self):
        self.alive = False
    def wait(self, timeout=None):
        return 0
    def kill(self):
        self.alive = False


@pytest.fixture
def mock_gpu(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "ROOT", tmp_path)
    monkeypatch.setattr(service, "capabilities",
                        lambda: {"available": True, "gpu": True})
    monkeypatch.setattr(service.shutil, "which", lambda name: "C:/ffmpeg.exe")
    monkeypatch.delenv("CINEMA_FFMPEG_PATH", raising=False)
    commands = []
    def launch(args, **_kwargs):
        commands.append(args)
        output = args[-1]
        from pathlib import Path
        folder = Path(output).parent
        (folder / "index.m3u8").write_text("#EXTM3U\n#EXTINF:2\nsegment_00000.ts\n")
        (folder / "segment_00000.ts").write_bytes(b"test data")
        return FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen", launch)
    service._SESSIONS.clear()
    yield commands
    for sid, record in list(service._SESSIONS.items()):
        service.stop(sid, record["owner"])


def test_cuda_pipeline_and_session_owner(mock_gpu):
    record = service.start("C:/Films/Movie 720p.mp4", "login-1", 1080,
                           "lanczos")
    args = mock_gpu[0]
    assert args[args.index("-hwaccel") + 1] == "cuda"
    assert args[args.index("-c:v") + 1] == "h264_nvenc"
    assert "scale_cuda=w=-2:h=1080:interp_algo=lanczos" in args
    assert "C:/Films/Movie 720p.mp4" in args
    assert service.get_owned(record["id"], "login-2") is None
    assert service.get_owned(record["id"], "login-1") is record
    assert service.asset(record, "index.m3u8").is_file()
    assert service.asset(record, "segment_00000.ts").is_file()
    assert service.asset(record, "../../ffmpeg.log") is None
    assert service.asset(record, "ffmpeg.log") is None
    assert service.telemetry(record)["running"] is True
    assert service.stop(record["id"], "login-2") is False
    assert service.stop(record["id"], "login-1") is True
    assert not record["directory"].exists()


def test_limits_one_encoder_and_validates_parameters(mock_gpu):
    with pytest.raises(ValueError):
        service.start("example.mp4", "user", 2160)
    with pytest.raises(ValueError):
        service.start("example.mp4", "user", 720, "inject;bad")
    record = service.start("example.mp4", "user", 720, "bicubic")
    with pytest.raises(service.UpscaleUnavailable):
        service.start("example2.mp4", "user", 720, "bicubic")
    assert service.stop(record["id"], "user")
