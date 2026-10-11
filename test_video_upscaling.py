from pathlib import Path

def read(path):
    return Path(path).read_text(encoding="utf-8")

def test_fsr_has_local_shader_assets_and_neural_mode_is_distinct():
    easu = read("static/shaders/fsr-easu.frag")
    rcas = read("static/shaders/fsr-rcas.frag")
    player = read("static/js/player_upscale.js")
    assert "FsrEasuF" in easu
    assert "FsrRcasF" in rcas
    assert "webgl2" in player
    assert "targetFsrSize" in player
    assert "1920 * 1080" in read("static/js/player_upscale_geometry.js")
    assert "cinema_upscale_mode" in player
    assert "teardownUpscale" in read("static/js/player.js")
    assert "injectUpscaleControl" in read("static/js/player_video.js")
    assert "injectNeuralControl" in read("static/js/player_video.js")

def test_native_neural_launch_is_restricted_and_safe():
    routes = read("routes/api_video.py")
    assert '@video_bp.route("/api/play/upscaled", methods=["POST"])' in routes
    assert "is_direct_local_request()" in routes
    assert "_catalog_item(path)" in routes
    assert 'os.path.isfile(shader)' in routes
    assert '"--glsl-shader=" + shader' in routes
    assert 'subprocess.Popen([' in routes
    assert "shell=True" not in routes

def test_wand_reports_click_results_and_caches_are_refreshed():
    video = read("static/js/player_video.js")
    renderer = read("static/js/player_upscale.js")
    style = read("static/css/style/player-upscale.css")
    entry = read("templates/cinema_home.html")
    panel = read("static/js/player_upscale_panel.js")
    assert "toggleUpscalePanel" in video
    assert "aria-live" in read("templates/components/video_modal.html")
    assert "wand.dataset.upscaleMode" in panel
    assert "data-upscale-mode=\"balanced\"" in style
    assert "data-upscale-mode=\"sharp\"" in style
    assert "video.addEventListener('seeked', renderFrame)" in renderer
    assert "video.addEventListener('loadeddata', renderFrame)" in renderer
    assert "window.addEventListener('resize', renderFrame)" in renderer
    assert "renderFrame(); // Work when paused" in renderer
    assert "mode = 'off';" in renderer
    assert "v22_retina_fsr" in entry
    assert '"./player_upscale.js"' in entry


def test_upscale_browser_smoke_is_part_of_ci():
    ci = read(".github/workflows/ci.yml")
    assert "tests/browser_upscale_smoke.py" in ci

def test_gpu_server_and_browser_paths_are_distinct():
    panel = read("static/js/player_upscale_panel.js")
    service = read("server_upscale_service.py")
    api = read("routes/api_upscale.py")
    ui = read("templates/components/video_modal.html")
    hls = read("static/js/player_server_stream.js")
    prefs = read("static/js/player_upscale_prefs.js")
    assert "GTX 1050 Ti" in ui
    assert "upscale-strength" in ui
    assert "upscale-preset" in ui
    assert "upscale-cap" in ui
    assert "upscale-auto" in ui
    assert "getVideoPlaybackQuality" in read("static/js/player_upscale_quality.js")
    assert "createDropMonitor" in read("static/js/player_upscale.js")
    assert "getUpscalePrefs" in prefs and "localStorage.setItem" in prefs
    assert "startServerStream" in panel
    assert "h264_nvenc" in service and "scale_cuda" in service
    assert "-init_hw_device" in service and "hwupload" in service and "cuda" in service
    assert "poorSpeedSamples >= 2" in hls
    assert "get_session_state" in api
    assert "check_path_safe(path)" in api
    assert "stream_status" in api
    assert "get_owned" in service
    assert "shell=True" not in service

def test_saved_upscale_autostarts_and_canvas_stays_below_controls():
    player = read("static/js/player_video.js")
    modal = read("static/js/player.js")
    panel = read("static/js/player_upscale_panel.js")
    renderer = read("static/js/player_upscale.js")
    streaming = read("static/js/player_server_stream.js")
    css = read("static/css/style/player-upscale.css")
    smoke = read("tests/browser_upscale_smoke.py")
    assert "restoreSavedUpscale(v.full_path, video" in player
    assert "cancelSavedUpscale();" in player
    assert "cancelSavedUpscale();" in modal
    assert "export async function restoreSavedUpscale" in panel
    assert "prefs.source !== 'server'" in panel
    assert "await startServerStream(path" in panel
    assert "getMedia()?.full_path !== path" in panel
    assert "video.closest('#video-modal .plyr__video-wrapper')" in renderer
    assert "mediaLayer.appendChild(canvas)" in renderer
    assert "stage.appendChild(canvas)" not in renderer
    assert "isolation: isolate" in css
    assert "pointer-events: none" in css
    assert "const pendingStop = stopServerStream()" in streaming
    assert "requestToken !== sequence" in streaming
    assert "auto_result" in smoke
    assert 'geometry["canvasZ"] < geometry["controlsZ"]' in smoke

def test_server_gpu_readiness_is_visible_and_real():
    panel = read("static/js/player_upscale_panel.js")
    ui = read("templates/components/video_modal.html")
    backend = read("server_upscale_service.py")
    assert "upscale-gpu-readiness" in ui
    assert "checkGpuReadiness" in panel
    assert "/api/upscale/capabilities" in panel
    assert "GPU SERVER CHƯA HOẠT ĐỘNG" in panel
    assert "CUDA_NVENC_PROBE_FAILED" in backend
    assert "testsrc2=size=160x90:rate=1" in backend
    assert "format=nv12,hwupload,scale_cuda" in backend
    assert "_diagnose_failure" in backend

def test_mac_retina_fsr_reports_only_real_gpu_processing():
    geometry = read("static/js/player_upscale_geometry.js")
    renderer = read("static/js/player_upscale.js")
    panel = read("static/js/player_upscale_panel.js")
    assert "vw * density" in geometry and "vh * density" in geometry
    assert "kind: 'sharpen'" in geometry
    assert "targetFsrSize" in renderer
    assert "window.devicePixelRatio" in renderer
    assert "processing = isRendering" in renderer
    assert "stateValue.processing" in panel
    assert "stateValue.renderInfo.width" in panel
    assert "FSR CHƯA XỬ LÝ" in panel
    assert "deviceScaleFactor" not in geometry
