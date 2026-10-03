import { state } from './state.js';
import { escapeHtml, escapeInlineJsSingleQuoted } from './security.js';
import { getStreamUrl } from './api.js';
import { playerRuntime } from './player_runtime.js';

const PROGRESS_SAVE_INTERVAL_MS = 3000;
let lastProgressSaveAt = 0;

export function getCurrentMedia() {
    return state.currentGridVideos[state.currentIndex] || null;
}

function stopAndUnloadVideo(video) {
    if (state.player) state.player.pause();
    video.pause?.();
    video.removeAttribute('src');
    video.load?.();
}

function ensurePlayer(video) {
    if (state.player) return;

    state.player = new Plyr(video, {
        controls: [
            'play-large', 'restart', 'rewind', 'play', 'fast-forward', 'progress',
            'current-time', 'duration', 'mute', 'volume', 'captions', 'settings',
            'pip', 'airplay', 'fullscreen'
        ],
        fullscreen: { container: '#video-modal' },
        seekTime: 10,
        i18n: {
            restart: 'Phát lại', rewind: 'Tua lại {seektime}s', play: 'Phát',
            pause: 'Tạm dừng', fastForward: 'Tua nhanh {seektime}s',
            seek: 'Tua', seekLabel: '{currentTime}s',
            played: 'Đã phát', buffered: 'Đã tải',
            currentTime: 'Thời gian hiện tại', duration: 'Thời lượng',
            enterFullscreen: 'Toàn màn hình', exitFullscreen: 'Thoát toàn màn hình',
        }
    });

    state.player.on('ended', () => {
        const current = getCurrentMedia();
        if (current?.full_path) {
            localStorage.removeItem('resume_' + current.full_path);
        }
        if (playerRuntime.isAutoNext) window.playNext?.(true);
    });

    state.player.on('timeupdate', () => {
        const now = Date.now();
        if (!state.player || state.player.currentTime <= 5 || now - lastProgressSaveAt < PROGRESS_SAVE_INTERVAL_MS) {
            return;
        }

        const current = getCurrentMedia();
        if (!current?.full_path) return;

        localStorage.setItem('resume_' + current.full_path, String(state.player.currentTime));
        lastProgressSaveAt = now;
    });

    state.player.on('error', (e) => {
        console.warn("Player error:", e);
        const current = getCurrentMedia();
        if (current) {
            renderFallbackUI(video.parentElement, current, "Không thể giải mã video này trên trình duyệt");
        }
    });
}

export function loadVideoSource(v) {
    playerRuntime.currentRotation = 0;
    const video = document.getElementById('modal-player') || state.player?.media;
    if (!video) return;

    video.style.transform = '';

    const fallback = video.parentElement?.querySelector('.fallback-overlay');
    if (fallback) fallback.style.display = 'none';

    const ext = (v.ext || '').toLowerCase();
    if (ext === '.ts' || ext === '.m2ts') {
        stopAndUnloadVideo(video);
        renderFallbackUI(video.parentElement, v, "Trình duyệt không hỗ trợ định dạng này (.TS)");
        return;
    }

    ensurePlayer(video);

    const requestedPath = v.full_path;
    const resumeTime = Number.parseFloat(localStorage.getItem('resume_' + requestedPath) || '0');

    if (Number.isFinite(resumeTime) && resumeTime > 5) {
        state.player.once('loadedmetadata', () => {
            const current = getCurrentMedia();
            if (!current || current.full_path !== requestedPath) return;

            const duration = Number(state.player.duration);
            const safeTime = Number.isFinite(duration) && duration > 1
                ? Math.min(resumeTime, duration - 1)
                : resumeTime;
            state.player.currentTime = Math.max(0, safeTime);
        });
    }

    state.player.source = {
        type: 'video',
        title: v.name,
        sources: [{ src: getStreamUrl(v.full_path) }]
    };

    lastProgressSaveAt = 0;
    setTimeout(injectPlyrCustomControls, 0);
    state.player.play().catch(() => { });
}

function injectPlyrCustomControls() {
    const controls = document.querySelector('.plyr__controls');
    if (controls) {
        // Rotation Button
        if (!document.getElementById('plyr-btn-rotate')) {
            const btn = document.createElement('button');
            btn.id = 'plyr-btn-rotate';
            btn.type = 'button';
            btn.className = 'plyr__control type-custom';
            btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i>';
            btn.onclick = () => window.rotateVideo();

            // Insert before exit fullscreen or end
            const pBtn = controls.querySelector('#plyr-btn-playlist');
            if (pBtn) controls.insertBefore(btn, pBtn);
            else {
                const fsBtn = controls.querySelector('[data-plyr="fullscreen"]');
                if (fsBtn) controls.insertBefore(btn, fsBtn);
                else controls.appendChild(btn);
            }
        }

        // Playlist Button
        if (!document.getElementById('plyr-btn-playlist')) {
            const btn = document.createElement('button');
            btn.id = 'plyr-btn-playlist';
            btn.type = 'button';
            btn.className = 'plyr__control type-custom';
            btn.innerHTML = '<i class="fa-solid fa-list-ul"></i>';
            btn.onclick = () => window.togglePlaylist();

            const fsBtn = controls.querySelector('[data-plyr="fullscreen"]');
            if (fsBtn) controls.insertBefore(btn, fsBtn);
            else controls.appendChild(btn);
        }
    }
}

window.rotateVideo = () => {
    const video = document.getElementById('modal-player');
    if (!video) return;

    playerRuntime.currentRotation = (playerRuntime.currentRotation + 90) % 360;

    if (playerRuntime.currentRotation === 90 || playerRuntime.currentRotation === 270) {
        // Tính toán scale để không bị crop khi xoay dọc trong container ngang
        const container = video.parentElement;
        const rect = container.getBoundingClientRect();

        // OffsetWidth/Height của video trước khi xoay
        const scale = Math.min(rect.width / video.offsetHeight, rect.height / video.offsetWidth);
        video.style.transform = `rotate(${playerRuntime.currentRotation}deg) scale(${scale})`;
    } else {
        video.style.transform = `rotate(${playerRuntime.currentRotation}deg) scale(1)`;
    }
};


