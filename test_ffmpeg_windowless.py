import os
import subprocess
import sys
from unittest.mock import patch, MagicMock

import pytest

import ffmpeg_runtime
import ffmpeg_service as ff
import ffmpeg_conversion
import services.ffmpeg_core as core
import services.ffmpeg_processor as proc


def test_ffmpeg_subprocess_kwargs_flag_mapping():
    kwargs = ffmpeg_runtime.ffmpeg_subprocess_kwargs(timeout=10)
    assert kwargs["timeout"] == 10
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
    else:
        assert "creationflags" not in kwargs


def test_ffmpeg_subprocess_kwargs_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(ffmpeg_runtime, "WINDOWS_CREATE_NO_WINDOW", 0)
    kwargs = ffmpeg_runtime.ffmpeg_subprocess_kwargs(text=True)
    assert kwargs == {"text": True}


def test_generate_thumbnail_passes_windowless_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success = ff.generate_thumbnail("video.mp4", "thumb.jpg")
        assert success is True
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_generate_preview_passes_windowless_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success = ff.generate_preview("video.mp4", "preview.mp4")
        assert success is True
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_get_video_duration_passes_windowless_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="123.45\n")
        duration = ff.get_video_duration("video.mp4")
        assert duration == 123.45
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_check_ffmpeg_presence_passes_windowless_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert ff.check_ffmpeg_presence() is True
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_remux_ts_to_mp4_passes_windowless_flag():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success = ffmpeg_conversion.remux_ts_to_mp4(
            "test.ts", "test.mp4", ffmpeg_runtime.FFMPEG_SEMAPHORE
        )
        assert success is True
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW
