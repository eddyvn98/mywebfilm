"""Real WebGL2 smoke test in Chrome: actual shaders, video frames, pause and resize."""
import http.server
import pathlib
import shutil
import socketserver
import threading
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_args):
        pass


def run():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        raise RuntimeError("Chrome/Chromium not installed; cannot verify WebGL2 upscaling")
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    executable_path=chrome,
                    headless=True,
                    args=["--enable-webgl", "--enable-unsafe-swiftshader", "--use-angle=swiftshader-webgl"],
                )
                page = browser.new_page(viewport={"width": 1100, "height": 700})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_address[1]}/tests/upscale_harness.html")
                page.set_content("""
                  <link rel="stylesheet" href="/static/css/style/player-upscale.css">
                  <div id="video-modal">
                    <div class="player-stage" style="position:relative;width:960px;height:540px">
                      <div class="plyr" style="position:relative;width:100%;height:100%">
                        <div class="plyr__video-wrapper" style="width:100%;height:100%">
                          <video id="modal-player" muted playsinline></video>
                        </div>
                        <div class="plyr__controls" style="position:absolute;bottom:0;height:65px;width:100%">
                          <button type="button" data-plyr="play">Play</button>
                        </div>
                      </div>
                    </div>
                  </div>
                """)
                page.evaluate("""async () => {
                  const mod = await import('/static/js/player_upscale.js');
                  window.upscaling = mod;
                  const source = document.createElement('canvas');
                  source.width = 320; source.height = 180;
                  const ctx = source.getContext('2d');
                  let running = true;
                  function paint() {
                    if (!running) return;
                    ctx.fillStyle = '#2255aa';
                    ctx.fillRect(0, 0, 320, 180);
                    ctx.fillStyle = '#f6aa40';
                    ctx.fillRect((performance.now() / 10) % 200, 45, 80, 90);
                    requestAnimationFrame(paint);
                  }
                  paint();
                  window.stopPainting = () => { running = false; };
                  const video = document.getElementById('modal-player');
                  video.srcObject = source.captureStream(24);
                  const withTimeout = (promise, label) => Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error('Timed out: ' + label)), 8000))]);
                  await withTimeout(video.play(), 'video.play');
                  if (video.readyState < 2) await withTimeout(new Promise(resolve => video.addEventListener('loadeddata', resolve, { once:true })), 'loadeddata');
                  await mod.setUpscaleMode('balanced', video);
                }""")
                page.wait_for_function("""() =>
                  window.upscaling.getUpscaleState().status === 'FSR GPU đang hoạt động'""",
                  timeout=15000)
                assert page.locator("#cinema-fsr-canvas").count() == 1
                assert page.locator(".plyr__video-wrapper > #cinema-fsr-canvas").count() == 1
                # Canvas must stay inside the video stacking context below Plyr controls.
                geometry = page.evaluate("""() => {
                  const canvas = document.getElementById('cinema-fsr-canvas');
                  const box = document.querySelector('.plyr__video-wrapper');
                  const controls = document.querySelector('.plyr__controls');
                  return { inside: box.contains(canvas),
                    canvasZ: Number(getComputedStyle(canvas).zIndex),
                    controlsZ: Number(getComputedStyle(controls).zIndex),
                    canvasRight: canvas.getBoundingClientRect().right,
                    wrapperRight: box.getBoundingClientRect().right };
                }""")
                assert geometry["inside"]
                assert geometry["canvasZ"] < geometry["controlsZ"]
                assert geometry["canvasRight"] <= geometry["wrapperRight"] + 1
                assert page.locator("#modal-player").evaluate("(el) => el.style.opacity") == "0"
                # Validate persisted custom RCAS, adjustable cap, and rendered GPU frame.
                page.evaluate("""async () => {
                  const video = document.getElementById('modal-player');
                  await upscaling.configureUpscale({
                    source: 'browser', preset: 'custom', strength: 75,
                    cap: 720, auto: true
                  }, video);
                  window.upscalePrefs = (await import('/static/js/player_upscale_prefs.js')).getUpscalePrefs();
                }""")
                assert page.evaluate("upscalePrefs.preset") == "custom"
                assert page.evaluate("upscalePrefs.strength") == 75
                assert page.evaluate("upscalePrefs.cap") == 720
                page.wait_for_function("""() =>
                  window.upscaling.getUpscaleState().status === 'FSR GPU đang hoạt động'""",
                  timeout=10000)
                page.evaluate("""async () => {
                  const video = document.getElementById('modal-player');
                  video.pause();
                  await upscaling.setUpscaleMode('sharp', video);
                }""")
                page.wait_for_function("""() =>
                  window.upscaling.getUpscaleState().status === 'FSR GPU đang hoạt động'""",
                  timeout=10000)
                page.evaluate("""() => {
                  document.querySelector('.player-stage').style.width = '160px';
                  window.dispatchEvent(new Event('resize'));
                }""")
                page.wait_for_function("""() =>
                  window.upscaling.getUpscaleState().status.includes('không cần phóng to')""",
                  timeout=5000)
                assert page.locator("#modal-player").evaluate("(el) => el.style.opacity") == ""
                page.evaluate("""() => {
                  document.querySelector('.player-stage').style.width = '960px';
                  window.dispatchEvent(new Event('resize'));
                }""")
                page.wait_for_function("""() =>
                  window.upscaling.getUpscaleState().status === 'FSR GPU đang hoạt động'""",
                  timeout=5000)
                page.evaluate("""async () => {
                  await upscaling.setUpscaleMode('off', document.getElementById('modal-player'));
                  window.stopPainting();
                }""")
                assert page.locator("#cinema-fsr-canvas").count() == 0
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    run()
    print("WebGL2 FSR smoke test passed.")
