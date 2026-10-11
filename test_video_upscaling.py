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
