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
