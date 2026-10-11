// Local WebGL2 FSR 1.0 (EASU + RCAS). FSR is spatial, not neural AI.
const QUAD = `#version 300 es
in vec2 p;
void main() { gl_Position = vec4(p, 0., 1.); }`;
const MODES = new Set(['off', 'balanced', 'sharp']);
const KEY = 'cinema_upscale_mode';
let mode = MODES.has(localStorage.getItem(KEY)) ? localStorage.getItem(KEY) : 'off';
let renderer = null;
let currentVideo = null;
let active = false;
let lastTime = -1;
let frameCount = 0;
let started = 0;
let callbackId = 0;
let status = 'Tắt';
const listeners = new Set();

export function getUpscaleState() {
    return { mode, active, status, fps: started ? Math.round(frameCount * 1000 / Math.max(1, performance.now() - started)) : 0 };
}
export function onUpscaleChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
}
function notify() { for (const fn of listeners) fn(getUpscaleState()); }
function compile(gl, type, code) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, code);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const reason = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(reason || 'Shader compilation failed');
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
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
}
async function loadShaders() {
    const paths = ['/static/shaders/fsr-easu.frag', '/static/shaders/fsr-rcas.frag'];
    const responses = await Promise.all(paths.map(url => fetch(url, { credentials: 'same-origin' })));
    if (responses.some(r => !r.ok)) throw new Error('Không tải được shader FSR');
    return Promise.all(responses.map(r => r.text()));
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
function setupPass(gl, p, texture, w, h, sharpness) {
    gl.useProgram(p);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.uniform1i(gl.getUniformLocation(p, 'iChannel0'), 0);
    gl.uniform2f(gl.getUniformLocation(p, 'iResolution'), w, h);
    const loc = gl.getUniformLocation(p, 'sharpness');
    if (loc !== null) gl.uniform1f(loc, sharpness);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}
async function createRenderer(video) {
    const stage = document.querySelector('#video-modal .player-stage');
    if (!stage) throw new Error('Không tìm thấy vùng phát');
    const canvas = document.createElement('canvas');
    canvas.id = 'cinema-fsr-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;object-fit:contain';
    const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, preserveDrawingBuffer: false });
    if (!gl) throw new Error('Trình duyệt không hỗ trợ WebGL2');
    const [easu, rcas] = await loadShaders();
    const prog1 = program(gl, easu);
    const prog2 = program(gl, rcas);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
    for (const p of [prog1, prog2]) {
        const loc = gl.getAttribLocation(p, 'p');
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    }
    const framebuffer = gl.createFramebuffer();
    let src = null, intermediate = null, sw = 0, sh = 0, ow = 0, oh = 0;
    stage.appendChild(canvas);
    function draw() {
        if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return;
        const bounds = stage.getBoundingClientRect();
        const ratio = Math.min(bounds.width / video.videoWidth, bounds.height / video.videoHeight);
        // Cap GPU work at 1080p on entry-level GTX 1050 Ti.
        const cap = Math.min(1, Math.sqrt((1920 * 1080) / Math.max(1, video.videoWidth * ratio * video.videoHeight * ratio)));
        const w = Math.max(2, Math.round(video.videoWidth * ratio * cap));
        const h = Math.max(2, Math.round(video.videoHeight * ratio * cap));
        if (w < video.videoWidth || h < video.videoHeight) return;
        if (video.videoWidth !== sw || video.videoHeight !== sh || ow !== w || oh !== h) {
            if (src) gl.deleteTexture(src);
            if (intermediate) gl.deleteTexture(intermediate);
            sw = video.videoWidth; sh = video.videoHeight; ow = w; oh = h;
            src = allocate(gl, sw, sh);
            intermediate = allocate(gl, ow, oh);
            canvas.width = ow; canvas.height = oh;
            canvas.style.width = '100%'; canvas.style.height = '100%';
            canvas.style.objectFit = 'contain';
        }
        gl.bindTexture(gl.TEXTURE_2D, src);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, video);
        gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, intermediate, 0);
        if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('GPU framebuffer failed');
        gl.viewport(0, 0, ow, oh);
        setupPass(gl, prog1, src, ow, oh, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        setupPass(gl, prog2, intermediate, ow, oh, mode === 'sharp' ? 0.15 : 1.5);
        if (frameCount === 0) { video.style.opacity = '0'; canvas.style.display = 'block'; started = performance.now(); }
        frameCount++;
        if (frameCount % 60 === 0) notify();
    }
    return { canvas, gl, draw, dispose() {
        canvas.remove();
        video.style.opacity = '';
        if (src) gl.deleteTexture(src);
        if (intermediate) gl.deleteTexture(intermediate);
        gl.deleteFramebuffer(framebuffer);
        gl.deleteBuffer(buffer);
        gl.deleteProgram(prog1); gl.deleteProgram(prog2);
    } };
}
function cancelLoop() {
    if (currentVideo && callbackId) {
        if (currentVideo.cancelVideoFrameCallback) currentVideo.cancelVideoFrameCallback(callbackId);
        else cancelAnimationFrame(callbackId);
    }
    callbackId = 0;
}
function schedule() {
    if (!active || !renderer || !currentVideo || currentVideo.paused || currentVideo.ended) return;
    const v = currentVideo;
    const tick = () => {
        if (!active || currentVideo !== v) return;
        try {
            if (v.currentTime !== lastTime && v.readyState >= 2) {
                renderer.draw();
                lastTime = v.currentTime;
            }
        } catch (err) {
            console.warn('FSR disabled:', err);
            status = 'GPU không thể xử lý video; đang dùng hình gốc';
            stopUpscale(false);
            return;
        }
        schedule();
    };
    callbackId = v.requestVideoFrameCallback
        ? v.requestVideoFrameCallback(tick)
        : requestAnimationFrame(tick);
}
function stopUpscale(resetStatus = true) {
    active = false;
    cancelLoop();
    if (renderer) { renderer.dispose(); renderer = null; }
    if (currentVideo) {
        currentVideo.removeEventListener('play', schedule);
        currentVideo.removeEventListener('pause', cancelLoop);
        currentVideo.removeEventListener('seeked', schedule);
    }
    currentVideo = null;
    frameCount = 0; started = 0; lastTime = -1;
    if (resetStatus) status = 'Tắt';
    notify();
}
export function teardownUpscale() { stopUpscale(); }
export async function setUpscaleMode(nextMode, video) {
    if (!MODES.has(nextMode)) return;
    mode = nextMode;
    localStorage.setItem(KEY, mode);
    stopUpscale();
    if (nextMode === 'off' || !video) return;
    currentVideo = video;
    status = 'Đang khởi tạo FSR...'; notify();
    try {
        const created = await createRenderer(video);
        if (currentVideo !== video || mode !== nextMode) { created.dispose(); return; }
        renderer = created;
        active = true; status = 'FSR GPU hoạt động';
        video.addEventListener('play', schedule);
        video.addEventListener('pause', cancelLoop);
        video.addEventListener('seeked', schedule);
        video.addEventListener('loadeddata', schedule, { once: true });
        schedule(); notify();
    } catch (err) {
        console.warn('FSR unavailable:', err);
        status = 'Không hỗ trợ GPU/WebGL2; phát video gốc';
        stopUpscale(false);
    }
}
export function restoreUpscale(video) {
    return setUpscaleMode(mode, video);
}
