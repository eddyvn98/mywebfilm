import { state } from './state.js';
import { getStreamUrl } from './api.js';
import { getUpscalePrefs, saveUpscalePrefs } from './player_upscale_prefs.js';
import { getUpscaleState, configureUpscale, teardownUpscale, onUpscaleChange } from './player_upscale.js';
import { startServerStream, stopServerStream, getServerStreamState, onServerStreamUpdate } from './player_server_stream.js';

let initialized = false;
let wand = null;
let serverStatus = '';
let serverSpeed = null;
let lastStatus = '';

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
        ? 'FSR 1 + RCAS dùng GPU thiết bị đang xem, không phải AI neural.'
        : 'Server GTX 1050 Ti: CUDA + NVENC → HLS. Tối đa 1080p, không phải AI neural. Tua phim có giới hạn.';
}
function showError(message) {
    const el = byId('upscale-panel-error');
    el.textContent = message;
    el.hidden = !message;
}
function drawState(stateValue) {
    const p = getUpscalePrefs();
    if (wand) {
        wand.dataset.upscaleMode = p.source === 'server' && getServerStreamState().active
            ? 'server' : stateValue.mode;
        wand.title = p.source === 'server' ? 'GTX server: ' + serverStatus
            : 'FSR ' + label(stateValue.mode) + ' · ' + stateValue.status;
        wand.setAttribute('aria-label', 'Cài đặt nâng nét: ' + wand.title);
        wand.setAttribute('aria-pressed', p.preset !== 'off' ? 'true' : 'false');
    }
    const drops = Number.isFinite(stateValue.dropped) ? stateValue.dropped : 'N/A';
    const speed = serverSpeed === null ? 'Chưa có' : serverSpeed.toFixed(2) + '×';
    const info = p.source === 'server' && getServerStreamState().active
        ? 'Server ' + getServerStreamState().height + 'p · Mã hóa ' + speed + ' · ' + serverStatus
        : 'FSR ' + stateValue.fps + ' FPS xử lý · Dropped frames: ' + drops
            + ' · Giới hạn thực tế: ' + stateValue.effectiveCap + 'p · ' + stateValue.status;
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
function restoreOriginal() {
    const v = getMedia();
    if (!v || !state.player) return;
    const player = state.player;
    player.source = { type: 'video', title: v.name,
        sources: [{ src: getStreamUrl(v.full_path) }] };
    player.play().catch(() => {});
}
async function apply() {
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
        const wasServer = getServerStreamState().active;
        if (settings.source === 'server' && settings.preset !== 'off') {
            const resume = wasServer ? 0 : Number(state.player.currentTime) || 0;
            teardownUpscale();
            await startServerStream(movie.full_path, { ...settings, startAt: resume }, video);
        } else {
            stopServerStream();
            if (wasServer) restoreOriginal();
            await configureUpscale(settings, state.player?.media || video);
        }
        hideUpscalePanel();
    } catch (error) {
        showError(error.message || 'Không thể bật GPU nâng nét');
        if (!getServerStreamState().active) restoreOriginal();
    } finally {
        applyButton.disabled = false;
        drawState(getUpscaleState());
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
