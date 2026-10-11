import { state } from './state.js';
import { getStreamUrl } from './api.js';
import { getUpscalePrefs, saveUpscalePrefs } from './player_upscale_prefs.js';
import { getUpscaleState, configureUpscale, restoreUpscale, teardownUpscale, onUpscaleChange } from './player_upscale.js';
import { startServerStream, stopServerStream, getServerStreamState, onServerStreamUpdate } from './player_server_stream.js';

let initialized = false;
let wand = null;
let serverStatus = '';
let serverSpeed = null;
let lastStatus = '';
let savedRestoreVersion = 0;
let lastGpuDiagnostic = null;
let diagnosticSerial = 0;

function byId(id) { return document.getElementById(id); }
function label(mode) {
    return { off: 'Tắt', balanced: 'Cân bằng', sharp: 'Sắc nét', custom: 'Tùy chỉnh' }[mode] || mode;
}
function getMedia() { return state.currentGridVideos[state.currentIndex]; }
function refreshInputs() {
    const p = getUpscalePrefs();
    byId('upscale-source').value = p.source;
    byId('upscale-preset').value = p.preset;
    byId('upscale-strength').value = String(p.strength);
    byId('upscale-cap').value = String(p.cap);
    byId('upscale-auto').checked = p.auto;
    updateDisabled();
}
function updateDisabled() {
    const source = byId('upscale-source').value;
    const preset = byId('upscale-preset').value;
    const strength = byId('upscale-strength');
    strength.disabled = source !== 'browser' || preset !== 'custom';
    byId('upscale-strength-output').textContent = strength.value + '%';
    byId('upscale-method').textContent = source === 'browser'
        ? 'FSR trên GPU máy đang xem: nhận biết màn hình Retina; video 1:1 vẫn làm nét RCAS.'
        : 'Server GTX 1050 Ti: giải mã CPU → nâng độ phân giải CUDA → mã hóa NVENC/HLS. Không phải AI neural.';
    void checkGpuReadiness();
}
async function checkGpuReadiness(force = false) {
    const target = byId('upscale-gpu-readiness');
    if (!target) return lastGpuDiagnostic;
    if (byId('upscale-source').value !== 'server') {
        target.hidden = true;
        return null;
    }
    target.hidden = false;
    if (!force && lastGpuDiagnostic) {
        target.textContent = lastGpuDiagnostic.available
            ? 'GPU server sẵn sàng · CUDA/NVENC đã thử mã hóa thành công'
            : 'GPU không sẵn sàng: ' + lastGpuDiagnostic.reason;
        return lastGpuDiagnostic;
    }
    const token = ++diagnosticSerial;
    target.textContent = 'Đang kiểm tra CUDA/NVENC thật trên server...';
    try {
        const response = await fetch('/api/upscale/capabilities', { cache: 'no-store' });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();
        if (token !== diagnosticSerial) return data;
        lastGpuDiagnostic = data;
        target.textContent = data.available
            ? 'GPU server sẵn sàng · CUDA/NVENC đã thử mã hóa thành công'
            : 'GPU không sẵn sàng: ' + (data.reason || 'Không xác định');
        return data;
    } catch (error) {
        if (token === diagnosticSerial) {
            target.textContent = 'Không kiểm tra được GPU server: ' + error.message;
        }
        return null;
    }
}

function showError(message) {
    const el = byId('upscale-panel-error');
    el.textContent = message;
    el.hidden = !message;
}
function drawState(stateValue) {
    const p = getUpscalePrefs();
    if (wand) {
        wand.dataset.upscaleMode = p.source === 'server'
            ? (getServerStreamState().active ? 'server' : 'off')
            : (stateValue.processing ? stateValue.mode : 'off');
        wand.title = p.source === 'server' ? 'GTX server: ' + serverStatus
            : 'FSR ' + label(stateValue.mode) + ' · ' + stateValue.status;
        wand.setAttribute('aria-label', 'Cài đặt nâng nét: ' + wand.title);
        wand.setAttribute('aria-pressed',
            (p.source === 'server' ? getServerStreamState().active : stateValue.processing)
                ? 'true' : 'false');
    }
    const drops = Number.isFinite(stateValue.dropped) ? stateValue.dropped : 'N/A';
    const speed = serverSpeed === null ? 'Chưa có' : serverSpeed.toFixed(2) + '×';
    const info = p.source === 'server'
        ? (getServerStreamState().active
            ? 'GPU SERVER ' + getServerStreamState().height + 'p · NVENC ' + speed + ' · ' + serverStatus
            : 'GPU SERVER CHƯA HOẠT ĐỘNG · ' + (serverStatus || 'Kiểm tra CUDA/NVENC'))
        : (stateValue.processing
            ? 'FSR WebGL2 · ' + stateValue.renderInfo.width + '×' +
                stateValue.renderInfo.height + ' pixel · Retina ' +
                stateValue.renderInfo.dpr.toFixed(1) + '× · ' +
                stateValue.fps + ' FPS xử lý · Drops: ' + drops +
                ' · ' + stateValue.status
            : 'FSR CHƯA XỬ LÝ · ' + stateValue.status);
    byId('upscale-metrics').textContent = info;
    if (lastStatus !== stateValue.status && lastStatus) {
        const notice = byId('player-upscale-notice');
        if (notice && stateValue.status.includes('Auto:')) {
            notice.textContent = stateValue.status;
            notice.hidden = false;
            setTimeout(() => { notice.hidden = true; }, 4500);
        }
    }
    lastStatus = stateValue.status;
}
function restoreOriginal(seekTo = 0) {
    const v = getMedia();
    if (!v || !state.player) return;
    const player = state.player;
    if (seekTo > 5) player.once('loadedmetadata', () => { player.currentTime = seekTo; });
    player.source = { type: 'video', title: v.name,
        sources: [{ src: getStreamUrl(v.full_path) }] };
    player.play().catch(() => {});
}
async function apply() {
    cancelSavedUpscale();
    const applyButton = byId('upscale-apply');
    const video = state.player?.media || byId('modal-player');
    const movie = getMedia();
    if (!video || !movie || !state.player) return;
    const settings = saveUpscalePrefs({
        source: byId('upscale-source').value,
        preset: byId('upscale-preset').value,
        strength: Number(byId('upscale-strength').value),
        cap: Number(byId('upscale-cap').value),
        auto: byId('upscale-auto').checked,
    });
    applyButton.disabled = true;
    showError('');
    try {
        const previousServer = getServerStreamState();
        const wasServer = previousServer.active;
        const resumePosition = Number(state.player.currentTime) || 0;
        const originalTime = wasServer ? previousServer.startAt + resumePosition : resumePosition;
        if (settings.source === 'server' && settings.preset !== 'off') {
            const available = await checkGpuReadiness(true);
            if (available && !available.available) {
                throw new Error(available.reason || 'GPU server chưa sẵn sàng');
            }
            const resume = originalTime;
            teardownUpscale();
            await startServerStream(movie.full_path, { ...settings, startAt: resume }, video);
        } else {
            stopServerStream();
            if (wasServer) restoreOriginal(originalTime);
            await configureUpscale(settings, state.player?.media || video);
        }
        hideUpscalePanel();
    } catch (error) {
        serverStatus = error.message || 'Không thể bật GPU nâng nét';
        showError(serverStatus);
        if (!getServerStreamState().active) restoreOriginal(originalTime);
    } finally {
        applyButton.disabled = false;
        drawState(getUpscaleState());
    }
}

export function cancelSavedUpscale() {
    ++savedRestoreVersion;
}
export async function restoreSavedUpscale(path, video, startAt = 0) {
    const version = ++savedRestoreVersion;
    const prefs = getUpscalePrefs();
    if (prefs.source !== 'server' || prefs.preset === 'off') {
        return restoreUpscale(video);
    }
    // Let Plyr finish replacing the media source before attaching the HLS stream.
    await new Promise(resolve => setTimeout(resolve, 150));
    if (version !== savedRestoreVersion || getMedia()?.full_path !== path) return;
    try {
        await startServerStream(path, { ...prefs, startAt: Math.max(0, startAt || 0) }, video);
        if (version !== savedRestoreVersion) return;
        const fallback = video.parentElement?.querySelector('.fallback-overlay');
        if (fallback) fallback.style.display = 'none';
        serverStatus = 'Đã khôi phục cấu hình GPU server';
        drawState(getUpscaleState());
    } catch (error) {
        if (version !== savedRestoreVersion) return;
        // The original stream is still playable and must remain visible on failure.
        serverStatus = 'Không thể tự bật xử lý server: ' + (error.message || 'GPU không sẵn sàng');
        showError(serverStatus);
        const notice = byId('player-upscale-notice');
        if (notice) {
            notice.textContent = serverStatus + ' · Đang phát phim gốc.';
            notice.hidden = false;
            setTimeout(() => { notice.hidden = true; }, 5500);
        }
        drawState(getUpscaleState());
        console.warn('[Auto GPU stream]', error);
    }
}

export function hideUpscalePanel() {
    const panel = byId('player-upscale-panel');
    if (panel) panel.hidden = true;
}
export function toggleUpscalePanel() {
    const panel = byId('player-upscale-panel');
    if (!panel) return;
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
        refreshInputs();
        showError('');
        drawState(getUpscaleState());
    }
}
export function initUpscalePanel(button) {
    wand = button;
    if (!initialized) {
        initialized = true;
        for (const id of ['upscale-source', 'upscale-preset', 'upscale-strength']) {
            byId(id).addEventListener('input', updateDisabled);
        }
        byId('upscale-close').addEventListener('click', hideUpscalePanel);
        byId('upscale-apply').addEventListener('click', () => { void apply(); });
        onUpscaleChange(drawState);
        onServerStreamUpdate(({ status, speed }) => {
            serverStatus = status;
            serverSpeed = speed;
            drawState(getUpscaleState());
        });
        setInterval(() => {
            if (!byId('player-upscale-panel').hidden) drawState(getUpscaleState());
        }, 1500);
    }
    drawState(getUpscaleState());
}
