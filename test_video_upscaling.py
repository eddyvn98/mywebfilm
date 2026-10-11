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
    assert "1920 * 1080" in player
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
    assert "showUpscaleStatus" in video
    assert "notice.setAttribute('role', 'status')" in video
    assert "btn.dataset.upscaleMode = mode;" in video
    assert "data-upscale-mode=\"balanced\"" in style
    assert "data-upscale-mode=\"sharp\"" in style
    assert "video.addEventListener('seeked', renderFrame)" in renderer
    assert "video.addEventListener('loadeddata', renderFrame)" in renderer
    assert "window.addEventListener('resize', renderFrame)" in renderer
    assert "renderFrame(); // Work when paused" in renderer
    assert "mode = 'off';" in renderer
    assert "v18_upscale_fix" in entry
    assert '"./player_upscale.js"' in entry


def test_upscale_browser_smoke_is_part_of_ci():
    ci = read(".github/workflows/ci.yml")
    assert "tests/browser_upscale_smoke.py" in ci
