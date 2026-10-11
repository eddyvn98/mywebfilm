import { getUpscalePrefs, saveUpscalePrefs, rcasStops } from './player_upscale_prefs.js';
import { createDropMonitor } from './player_upscale_quality.js';
// FSR 1 (EASU + RCAS), locally rendered on the viewer's WebGL2 GPU. Not neural AI.
const QUAD = `#version 300 es
in vec2 p;
void main() { gl_Position = vec4(p, 0., 1.); }`;
const MODES = new Set(['off', 'balanced', 'sharp', 'custom']);
const KEY = 'cinema_upscale_mode';
let mode = getUpscalePrefs().preset;
let renderer = null;
let currentVideo = null;
let active = false;
let callbackId = 0;
let generation = 0;
let frameCount = 0;
let started = 0;
let status = 'Tắt';
let lastFrameTime = -1;
let effectiveCap = getUpscalePrefs().cap;
let measuredFps = 0;
let fpsWindowAt = 0;
let fpsWindowFrames = 0;
const listeners = new Set();
const quality = createDropMonitor({ getPrefs: getUpscalePrefs,
    getCap: () => effectiveCap, setCap: cap => { effectiveCap = cap; },
    setStatus, fail: failUpscale, notify });

export function getUpscaleState() {
    return { mode, active, status, fps: measuredFps, dropped: quality.dropped(),
        effectiveCap, settings: getUpscalePrefs() };
}
export function onUpscaleChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
}
function notify() { for (const fn of listeners) fn(getUpscaleState()); }
function setStatus(value) {
    if (status !== value) { status = value; notify(); }
}
function compile(gl, type, code) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, code);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const error = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(error || 'Shader compilation failed');
    }
    return shader;
}
function program(gl, fragment) {
    const vert = compile(gl, gl.VERTEX_SHADER, QUAD);
    const frag = compile(gl, gl.FRAGMENT_SHADER, fragment);
    const p = gl.createProgram();
    gl.attachShader(p, vert);
    gl.attachShader(p, frag);
    gl.linkProgram(p);
    gl.deleteShader(vert);
    gl.deleteShader(frag);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
        const error = gl.getProgramInfoLog(p);
        gl.deleteProgram(p);
        throw new Error(error || 'Shader program link failed');
    }
    return p;
}
async function loadShaders() {
    const urls = ['/static/shaders/fsr-easu.frag', '/static/shaders/fsr-rcas.frag'];
    const responses = await Promise.all(urls.map(url => fetch(url, { credentials: 'same-origin', cache: 'no-cache' })));
    if (responses.some(res => !res.ok)) throw new Error('Không tải được shader FSR');
    return Promise.all(responses.map(res => res.text()));
}
function allocate(gl, w, h) {
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    return texture;
}
async function createRenderer(video) {
    // Place the processed frame INSIDE Plyr media, never above its controls.
    const mediaLayer = video.closest('#video-modal .plyr__video-wrapper');
    if (!mediaLayer) throw new Error('Không tìm thấy vùng hình ảnh Plyr');
    const canvas = document.createElement('canvas');
    canvas.id = 'cinema-fsr-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.className = 'cinema-fsr-canvas';
    canvas.style.display = 'none';
    const gl = canvas.getContext('webgl2', { alpha: false, antialias: false });
    if (!gl) throw new Error('Trình duyệt không hỗ trợ WebGL2');
    const [easu, rcas] = await loadShaders();
    const first = program(gl, easu), second = program(gl, rcas);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
    const framebuffer = gl.createFramebuffer();
    let src = null, intermediate = null, sw = 0, sh = 0, ow = 0, oh = 0;
    mediaLayer.appendChild(canvas);

    const contextLost = event => {
        event.preventDefault();
        failUpscale('GPU WebGL bị mất kết nối; đã trở về video gốc');
    };
    canvas.addEventListener('webglcontextlost', contextLost);
    function pass(p, texture, w, h, sharpness) {
        gl.useProgram(p);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        const loc = gl.getAttribLocation(p, 'p');
        if (loc >= 0) {
            gl.enableVertexAttribArray(loc);
            gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        }
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.uniform1i(gl.getUniformLocation(p, 'iChannel0'), 0);
        gl.uniform2f(gl.getUniformLocation(p, 'iResolution'), w, h);
        const sharp = gl.getUniformLocation(p, 'sharpness');
        if (sharp !== null) gl.uniform1f(sharp, sharpness);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    function showOriginal() {
        video.style.opacity = '';
        canvas.style.display = 'none';
    }
    function draw() {
        if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return 'waiting';
        const rect = mediaLayer.getBoundingClientRect();
        if (!rect.width || !rect.height) return 'waiting';
        const ratio = Math.min(rect.width / video.videoWidth, rect.height / video.videoHeight);
        // 1080p is the GTX 1050 Ti default; cap can be lowered automatically.
        const budget = 1920 * 1080 * Math.pow(effectiveCap / 1080, 2);
        const cap = Math.min(1, Math.sqrt(budget / Math.max(1, video.videoWidth * ratio * video.videoHeight * ratio)));
        const w = Math.max(2, Math.round(video.videoWidth * ratio * cap));
        const h = Math.max(2, Math.round(video.videoHeight * ratio * cap));
        if (w <= video.videoWidth || h <= video.videoHeight) {
            showOriginal();
            return 'native';
        }
        if (video.videoWidth !== sw || video.videoHeight !== sh || ow !== w || oh !== h) {
            if (src) gl.deleteTexture(src);
            if (intermediate) gl.deleteTexture(intermediate);
            sw = video.videoWidth; sh = video.videoHeight; ow = w; oh = h;
            src = allocate(gl, sw, sh);
            intermediate = allocate(gl, ow, oh);
            canvas.width = ow; canvas.height = oh;
        }
        gl.bindTexture(gl.TEXTURE_2D, src);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, video);
        gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, intermediate, 0);
        if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('GPU framebuffer failed');
        gl.viewport(0, 0, ow, oh);
        pass(first, src, ow, oh, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        pass(second, intermediate, ow, oh, rcasStops(mode));
        if (!frameCount) started = performance.now();
        frameCount++;
        fpsWindowFrames++;
        const now = performance.now();
        if (!fpsWindowAt) fpsWindowAt = now;
        if (now - fpsWindowAt >= 3000) {
            measuredFps = Math.round(fpsWindowFrames * 1000 / (now - fpsWindowAt));
            fpsWindowAt = now;
            fpsWindowFrames = 0;
            notify();
        }
        video.style.opacity = '0';
        canvas.style.display = 'block';
        if (frameCount % 120 === 0) notify();
        return 'processed';
    }
    return { draw, dispose() {
        canvas.removeEventListener('webglcontextlost', contextLost);
        showOriginal();
        canvas.remove();
        if (src) gl.deleteTexture(src);
        if (intermediate) gl.deleteTexture(intermediate);
        gl.deleteFramebuffer(framebuffer);
        gl.deleteBuffer(buffer);
        gl.deleteProgram(first);
        gl.deleteProgram(second);
    } };
}
function cancelLoop() {
    if (currentVideo && callbackId) {
        if (currentVideo.cancelVideoFrameCallback) currentVideo.cancelVideoFrameCallback(callbackId);
        else cancelAnimationFrame(callbackId);
    }
    callbackId = 0;
}
function renderFrame() {
    if (!active || !renderer || !currentVideo) return;
    try {
        const result = renderer.draw();
        if (result === 'processed') setStatus('FSR GPU đang hoạt động');
        if (result === 'native') setStatus('Video không cần phóng to ở kích thước hiện tại');
    } catch (err) {
        console.error('[Video upscaling]', err);
        failUpscale('FSR lỗi GPU/shader; đang phát video gốc');
    }
}
function schedule() {
    if (!active || !renderer || !currentVideo || currentVideo.paused || currentVideo.ended || callbackId) return;
    const video = currentVideo;
    const tick = () => {
        callbackId = 0;
        if (!active || currentVideo !== video) return;
        if (!video.requestVideoFrameCallback && video.currentTime === lastFrameTime) {
            schedule();
            return;
        }
        lastFrameTime = video.currentTime;
        renderFrame();
        quality.sample(video);
        schedule();
    };
    callbackId = video.requestVideoFrameCallback ? video.requestVideoFrameCallback(tick) : requestAnimationFrame(tick);
}
function stopUpscale(resetStatus = true) {
    generation++;
    active = false;
    cancelLoop();
    if (currentVideo) {
        currentVideo.removeEventListener('play', schedule);
        currentVideo.removeEventListener('pause', cancelLoop);
        currentVideo.removeEventListener('seeked', renderFrame);
        currentVideo.removeEventListener('loadeddata', renderFrame);
    }
    window.removeEventListener('resize', renderFrame);
    if (renderer) { renderer.dispose(); renderer = null; }
    currentVideo = null;
    frameCount = 0; started = 0; lastFrameTime = -1;
    effectiveCap = getUpscalePrefs().cap;
    quality.reset();
    measuredFps = 0; fpsWindowAt = 0; fpsWindowFrames = 0;
    if (resetStatus) status = 'Tắt';
    notify();
}
function failUpscale(message) {
    mode = 'off';
    saveUpscalePrefs({ preset: 'off' });
    try { localStorage.setItem(KEY, mode); } catch {}
    stopUpscale(false);
    setStatus(message);
}
export function teardownUpscale() { stopUpscale(); }
export async function setUpscaleMode(nextMode, video) {
    if (!MODES.has(nextMode)) return;
    mode = nextMode;
    saveUpscalePrefs({ preset: mode, source: 'browser' });
    try { localStorage.setItem(KEY, mode); } catch {}
    stopUpscale();
    if (nextMode === 'off' || !video) return;
    const token = generation;
    currentVideo = video;
    setStatus('Đang khởi tạo WebGL2...');
    try {
        const created = await createRenderer(video);
        if (token !== generation || currentVideo !== video || mode !== nextMode) {
            created.dispose();
            return;
        }
        renderer = created;
        active = true;
        setStatus('Đang chờ khung hình...');
        video.addEventListener('play', schedule);
        video.addEventListener('pause', cancelLoop);
        video.addEventListener('seeked', renderFrame);
        video.addEventListener('loadeddata', renderFrame);
        window.addEventListener('resize', renderFrame);
        renderFrame(); // Work when paused; also reveal GPU errors immediately.
        schedule();
    } catch (err) {
        if (token !== generation) return;
        console.error('[Video upscaling]', err);
        failUpscale('Không thể bật FSR (WebGL2/shader); đang phát gốc');
    }
}
export function restoreUpscale(video) {
    return getUpscalePrefs().source === 'browser' ? setUpscaleMode(mode, video) : Promise.resolve();
}
export function configureUpscale(changes, video) {
    const settings = saveUpscalePrefs(changes);
    if (settings.source !== 'browser') {
        teardownUpscale();
        return Promise.resolve();
    }
    return setUpscaleMode(settings.preset, video);
}
