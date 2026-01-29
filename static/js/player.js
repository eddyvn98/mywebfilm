// static/js/player.js
import { state } from './state.js';
import { getStreamUrl } from './api.js';

export function openVideoModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    const modal = document.getElementById('video-modal');
    modal.classList.remove('hidden');
    void modal.offsetWidth;
    modal.classList.add('translate-y-0');
    modal.classList.remove('translate-y-full');

    loadVideoSource(v);
}

export function closeVideoModal() {
    if (state.player) state.player.pause();
    const modal = document.getElementById('video-modal');
    modal.classList.add('translate-y-full');
    modal.classList.remove('translate-y-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

function loadVideoSource(v) {
    let video = document.getElementById('modal-player');
    if (!video && state.player) video = state.player.media;
    if (!video) {
        console.error("Player element not found");
        return;
    }

    // Check for unsupported formats immediately
    const ext = (v.ext || '').toLowerCase();
    if (ext === '.ts' || ext === '.m2ts') {
        renderFallbackUI(video.parentElement, v, "Trình duyệt không hỗ trợ định dạng này (.TS)");
        return;
    }

    const sourceUrl = getStreamUrl(v.full_path);

    if (state.player) {
        state.player.source = {
            type: 'video',
            sources: [{ src: sourceUrl }]
        };
    } else {
        video.src = sourceUrl;
    }

    // Resume position logic
    const savedTime = localStorage.getItem('resume_' + v.full_path);
    if (savedTime) {
        if (state.player) {
            state.player.once('ready', () => {
                state.player.currentTime = parseFloat(savedTime);
            });
        } else {
            video.currentTime = parseFloat(savedTime);
        }
    }

    if (!state.player) {
        state.player = new Plyr(video, {
            controls: [
                'play-large', 'play', 'progress', 'current-time', 'duration',
                'mute', 'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'
            ],
            i18n: {
                restart: 'Phát lại', play: 'Phát', pause: 'Tạm dừng',
                seek: 'Tua', seekLabel: '{currentTime}s',
                played: 'Đã phát', buffered: 'Đã tải',
                currentTime: 'Thời gian hiện tại', duration: 'Thời lượng',
                enterFullscreen: 'Toàn màn hình', exitFullscreen: 'Thoát toàn màn hình',
            }
        });

        // Error handling for other formats that might fail decoding
        state.player.on('error', (e) => {
            console.warn("Player error:", e);
            renderFallbackUI(video.parentElement, v, "Không thể giải mã video này trên trình duyệt");
        });

        state.player.on('timeupdate', () => {
            if (state.player && state.player.currentTime > 5) {
                localStorage.setItem('resume_' + v.full_path, state.player.currentTime);
            }
        });
    }

    state.player.play().catch(e => {
        console.log("Auto-play blocked, showing fallback:", e);
        // Don't show fallback immediately on autoplay block, user can click play.
        // But if it's a source error, the 'error' event will fire.
    });
}

function renderFallbackUI(container, v, msg) {
    // Hide video/hide player wrapper content if possible, or overlay
    // Ideally we append an overlay div
    let overlay = container.querySelector('.fallback-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'fallback-overlay absolute inset-0 z-50 bg-slate-900 flex flex-col items-center justify-center space-y-4 p-6 text-center';
        container.appendChild(overlay);
    }

    // Ensure we see it
    overlay.style.display = 'flex';

    overlay.innerHTML = `
        <div class="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center mb-2 animate-pulse">
            <i class="fa-solid fa-triangle-exclamation text-4xl text-yellow-500"></i>
        </div>
        <h3 class="text-white font-bold text-lg">${msg}</h3>
        <p class="text-slate-400 text-sm max-w-md">File <b>${v.name}</b> sử dụng định dạng mà trình duyệt web (Chrome/Edge) không thể phát trực tiếp.</p>
        
        <div class="flex gap-3 mt-4">
            <button onclick="playExternal('${v.full_path.replace(/\\/g, '\\\\')}')" 
                    class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-lg shadow-blue-900/50 transition transform active:scale-95 flex items-center gap-2">
                <i class="fa-solid fa-external-link-alt"></i> Mở bằng MPC-HC
            </button>
            <button onclick="closeVideoModal()" 
                    class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold transition">
                Đóng
            </button>
        </div>
    `;
}

// Global helper for the button
window.playExternal = async (path) => {
    // Import dynamically or assume api exists globally if we attached it?
    // We didn't attach api to window. Let's send a fetch directly or import.
    // Easier to just use fetch here since we are in module but button is global HTML.
    try {
        const res = await fetch('/api/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, type: 'video' })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            closeVideoModal();
        } else {
            alert("Lỗi không mở được: " + data.msg);
        }
    } catch (e) {
        alert("Lỗi kết nối: " + e);
    }
};

export function playNext() {
    if (state.currentIndex < state.currentGridVideos.length - 1) {
        state.currentIndex++;
        const next = state.currentGridVideos[state.currentIndex];
        if (next.type === 'image') playNext(); // Skip image
        else loadVideoSource(next);
    }
}

export function playPrev() {
    if (state.currentIndex > 0) {
        state.currentIndex--;
        const prev = state.currentGridVideos[state.currentIndex];
        if (prev.type === 'image') playPrev(); // Skip image
        else loadVideoSource(prev);
    }
}

window.closeVideoModal = closeVideoModal;
window.playVideoFromIndex = (idx) => {
    const v = state.currentGridVideos[idx];
    if (!v) return;
    if (v.type === 'image') window.open(getStreamUrl(v.full_path), '_blank');
    else openVideoModal(idx);
};
window.playStreamFromIndex = (event, idx) => {
    event.stopPropagation();
    window.playVideoFromIndex(idx);
};
