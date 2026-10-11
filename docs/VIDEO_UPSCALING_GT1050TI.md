# Realtime video upscaling (GTX 1050 Ti 4GB)

This feature has **two distinct processing paths**. Neither uses cloud APIs or tokens.

## 1. Web player: FSR 1.0 (not neural AI)
Open a movie in the normal MyWebFilm player. Click the magic-wand control to cycle:
Off -> Balanced -> Sharp -> Off.

- Uses local WebGL2 shader programs: AMD FSR 1 EASU + RCAS adaptation.
- Runs on the GPU of **the computer displaying the browser**, not automatically on the Windows media server.
- Caps processing at roughly 1920x1080 pixels; source video files and FFmpeg streaming are unchanged.
- Automatically falls back to original video if WebGL2 is unavailable, the GPU context fails, or shaders cannot be loaded.
- If the video is higher resolution than the output, native playback remains visible.
- View at fullscreen with 480p/720p files first. If frame drops occur, choose Off.
- Spatial upscaling may improve perceived edges but does **not** reconstruct reliable lost detail like neural super-resolution.

The shader sources in static/shaders are adapted from Hajime-san/web-fsr (MIT license included).

## 2. Windows host: mpv + FSRCNNX (neural AI)

This mode is only enabled from a **direct localhost session on the Windows machine running MyWebFilm**. It launches a separate desktop player. It does not stream AI-upscaled frames to remote clients.

1. Install current Windows mpv (https://mpv.io/installation/).
2. Download FSRCNNX_x2_8-0-4-1.glsl from https://github.com/igv/FSRCNN-TensorFlow/releases .
3. Save the shader at a fixed local path, e.g. C:\\CinemaShaders\\FSRCNNX_x2_8-0-4-1.glsl.
4. Set system environment variables before starting MyWebFilm:
   - CINEMA_MPV_PATH=C:\\Program Files\\mpv\\mpv.exe (adjust to actual installation)
   - CINEMA_FSRCNNX_SHADER=C:\\CinemaShaders\\FSRCNNX_x2_8-0-4-1.glsl
5. Restart MyWebFilm. Open http://localhost:5000 in a browser *on the Windows host*; click the microchip button in the movie player's controls.

The API returns HTTP 503 when mpv/shader is missing and HTTP 403 for unauthorized media or non-local calls. Shell commands are never constructed from user input: the media path is catalog-validated and passed as its own subprocess argument. The Windows host must be running in an interactive desktop session for mpv to display.

FSRCNNX is licensed separately by its author (LGPL); it is **not** bundled into this repository.

## Validation checklist

- Browser WebGL2: launch 720p movie, turn FSR on/off, seek, pause, fullscreen, change movie and close modal.
- Compare with original video for artifacts, ringing, over-sharpening and dropped frames.
- No WebGL2: original video should still play.
- Off/On modes: preserve seek position; avoid altering files.
- GPU and CPU: use Windows Task Manager -> Performance -> GPU and browser playback statistics.
- Local mpv: validate successful launch and shader use, then test the missing mpv/shader responses.
- Cloudflare remote sessions must *not* trigger native desktop launches.
- CI validates Python syntax, JavaScript syntax and static player contracts. Actual GPU FPS requires Windows GTX 1050 Ti hardware and a browser smoke test.

Important: Neither "Balanced" nor "Sharp" is neural AI. True neural upscaling requires launching the separately configured FSRCNNX player.

## Wand troubleshooting and status (October 2026 fix)

- The wand has a **blue background** in Balanced, **green background** in Sharp, and no highlight when Off. A short on-screen message confirms the actual GPU state or explains why upscaling is unavailable.
- If the browser has no WebGL2 or the shaders fail, the source video remains available and the status reports the failure (not a silent no-op).
- Paused video, seeking, switching movie, browser resizing and leaving fullscreen now all update or stop the renderer.
- At 1:1 or downscaled display size, the source video remains visible; there is nothing to spatially upscale. Increase the playback area or use 480p/720p content to test.
- After deploying, use Ctrl+Shift+R once to invalidate previous JS/CSS. The import map now uses v18_upscale_fix.
- Chrome/Edge: open DevTools Console and check [Video upscaling] for technical shader errors if the status reports a failure.
- CI runs an actual headless Chrome WebGL2 smoke test in addition to syntax and static tests.


## Web player settings + GTX server streaming (October 2026)

The wand now opens a settings panel instead of cycling blindly.

- **Browser GPU / FSR 1:** Presets Off, Balanced (1.5 RCAS stops), Sharp (0.15 stops), Custom (RCAS 0–100%). Cap 720/1080/1440/2160p. Local settings persist in browser storage. Frame presentation drops are taken from `getVideoPlaybackQuality()`; processed FPS is estimated by the rendering loop.
- **Auto in browser mode:** At least six dropped frames during each of two consecutive 8-second windows triggers stepdown of output resolution to 720p then 540p; if it still stutters, FSR is disabled and original video returns. Frame drops may also originate from decoding/network, not just shader GPU load.
- **Server GPU / HLS:** Opt-in FFmpeg NVIDIA CUDA spatial scaling + NVENC H.264/AAC, sent over authenticated HLS segments. GTX 1050 Ti work happens **on the Windows server**, unlike browser mode. Server preset Balanced uses bicubic interpolation; Sharp/Custom uses Lanczos. RCAS slider is browser-only.
- The server's render cap is limited to 1080p on GTX 1050 Ti even if the browser setting is 1440p/4K. One server encode session at a time; other requests return 503.
- Server Auto monitors FFmpeg `speed`: two consecutive samples below 0.85× trigger a 1080→720→540p restart from approximate playback position. **The restart briefly rebuffers and resets the HLS timeline**; seamless adaptive streaming and arbitrary seeking are not yet supported.
- Files remain unchanged. Backend validates the media path against the catalog and binds random stream IDs to the authenticated login session; an idle stream is killed after three minutes.
- Server GPU processing is **spatial upscaling, not neural AI**. The separate mpv/FSRCNNX button is still local-only and does not stream to remote viewers. Neural upscaling with FSRCNNX as server HLS requires a separately validated processing pipeline and GTX 1050 Ti benchmark.

### Windows setup

1. Install NVIDIA driver and an FFmpeg Windows build that lists both `scale_cuda` (`ffmpeg -filters`) and `h264_nvenc` (`ffmpeg -encoders`). To set a custom executable: `CINEMA_FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe`.
2. Restart MyWebFilm on Windows. Open from any browser with supported HLS.js/MediaSource, authenticate, play a film and click the wand.
3. Set **Nơi xử lý: GTX 1050 Ti trên server**, choose Balanced or Sharp, resolution 720p first, then select Apply.
4. If this fails, MyWebFilm reports a 503 instead of silently using the browser GPU. Check the NVIDIA driver, FFmpeg build and browser Console. Server FFmpeg logs are private under `data/gpu_hls/<session-id>/ffmpeg.log` until cleanup.
5. To test performance, use Windows Task Manager → GPU → Video Encode/Decode and compare FFmpeg encoding speed in the settings panel. Do not expect the viewer's GPU to show NVENC work.
6. If video is delivered over Cloudflare Tunnel, transcoding consumes **server GPU and outgoing network bandwidth**; no paid AI tokens are used.

### Known limitations

- HLS is an experimental progressive transcoding stream; seeking across unencoded parts of long movies is limited. Source subtitles are not yet repackaged into the transcoded HLS stream.
- GTX 1050 Ti NVDEC may not handle every source codec/pixel format; an unsupported file can fail GPU startup instead of transcoding. The original source playback remains available.
- The CI unit tests mock NVENC, and browser tests exercise shader rendering; they cannot prove that a physical GTX 1050 Ti sustains 24/30/60 FPS or that a specific FFmpeg Windows build supports the GPU.
