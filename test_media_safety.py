from types import SimpleNamespace

import ffmpeg_service as ff


def _fake_successful_ffmpeg(monkeypatch):
    def fake_run(cmd, *args, **kwargs):
        output = cmd[-1]
        if isinstance(output, str) and output.endswith('.partial.mp4'):
            with open(output, 'wb') as f:
                f.write(b'fake-video')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(ff.subprocess, 'run', fake_run)


def test_highlight_keeps_source_when_validation_fails(tmp_path, monkeypatch):
    source = tmp_path / 'source.mp4'
    source.write_bytes(b'original')
    out_dir = tmp_path / 'Processed'
    _fake_successful_ffmpeg(monkeypatch)
    monkeypatch.setattr(ff, 'validate_media_output', lambda path: False)

    result = ff.process_highlight_video(str(source), str(out_dir), delete_src=True)

    assert result is None
    assert source.exists()
    assert not (out_dir / 'source_highlight.mp4').exists()


def test_highlight_deletes_source_only_after_validated_output(tmp_path, monkeypatch):
    source = tmp_path / 'source.mp4'
    source.write_bytes(b'original')
    out_dir = tmp_path / 'Processed'
    _fake_successful_ffmpeg(monkeypatch)
    monkeypatch.setattr(ff, 'validate_media_output', lambda path: True)

    result = ff.process_highlight_video(str(source), str(out_dir), delete_src=True)

    assert result == str(out_dir / 'source_highlight.mp4')
    assert not source.exists()
    assert (out_dir / 'source_highlight.mp4').exists()
