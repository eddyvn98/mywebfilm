// static/js/player.js
import { state } from './state.js';
import { escapeHtml, escapeAttr, escapeInlineJsSingleQuoted } from './security.js';
import { getStreamUrl, getThumbnailUrl } from './api.js';
import { historyService } from './history_service.js';
import { favoritesService } from './favorites_service.js';

let isAutoNext = false;
let isShuffle = false;
let currentRotation = 0;
let lastProgressSaveAt = 0;
let historyRecordTimer = null;
const PROGRESS_SAVE_INTERVAL_MS = 3000;
const HISTORY_RECORD_DELAY_MS = 1500;
const PLAYLIST_WINDOW_RADIUS = 40;
let playlistRenderedForLength = -1;

export function openVideoModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    // Inject UI if missing
    if (!document.getElementById('playlist-sidebar')) {
        injectPlaylistUI();
    }

    const modal = document.getElementById('video-modal');
    const isOpeningModal = modal.classList.contains('hidden');
    modal.classList.remove('hidden');
    if (isOpeningModal) {
        void modal.offsetWidth;
    }
    modal.classList.add('translate-y-0');
    modal.classList.remove('translate-y-full');

    // Update Title & Favorite
    const titleEl = document.getElementById('video-modal-title');
    if (titleEl) titleEl.textContent = v.name;
    updatePlayerFavoriteUI(v.full_path);

    scheduleHistoryRecord(v);

    loadVideoSource(v);

    const playlist = document.getElementById('playlist-content');
    if (playlist && (playlist.children.length === 0 || playlistRenderedForLength !== state.currentGridVideos.length)) {
        renderPlaylist();
    } else {
        renderPlaylistWindow();
    }
}

function scheduleHistoryRecord(video) {
    clearTimeout(historyRecordTimer);
    historyRecordTimer = setTimeout(() => {
        historyService.addToHistory(video);
        historyRecordTimer = null;
    }, HISTORY_RECORD_DELAY_MS);
}

function injectPlaylistUI() {
    const modal = document.getElementById('video-modal');

    // Sidebar HTML
    const sidebar = document.createElement('div');
    sidebar.id = 'playlist-sidebar';
    sidebar.innerHTML = `
        <div class="p-4 border-b border-white/10 flex justify-between items-center bg-slate-900/95 sticky top-0 z-10 backdrop-blur">
            <h3 class="text-sm font-bold uppercase tracking-widest text-white">Danh sách phát</h3>
            <button onclick="togglePlaylist()" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="p-3 border-b border-white/5 flex items-center justify-between bg-slate-900/50">
            <div class="flex items-center gap-3">
                <label class="flex items-center gap-2 cursor-pointer group">
                    <div class="relative w-8 h-4 rounded-full bg-slate-700 transition group-hover:bg-slate-600">
                        <input type="checkbox" id="auto-next-toggle" class="peer sr-only" onchange="toggleAutoNext(this)">
                        <div class="absolute left-0.5 top-0.5 w-3 h-3 bg-white rounded-full transition peer-checked:translate-x-4 peer-checked:bg-blue-400"></div>
                    </div>
                    <span class="text-[10px] font-bold uppercase text-slate-400 peer-checked:text-blue-400 select-none">Tự động chuyển</span>
                </label>
            </div>
            <button id="btn-shuffle" onclick="toggleShuffle()" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-blue-600/20 hover:text-blue-400 transition text-slate-500">
                <i class="fa-solid fa-shuffle text-xs"></i>
            </button>
        </div>
        <div id="playlist-content" class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1"></div>
    `;
    modal.appendChild(sidebar);

    // Add Overlay for Playlist
    const overlay = document.createElement('div');
    overlay.id = 'playlist-overlay';
    overlay.className = 'fixed inset-0 bg-black/50 z-[1400] hidden transition-opacity duration-300 opacity-0';
    overlay.onclick = () => togglePlaylist(false);
    modal.appendChild(overlay);

    // Initial state setup
    document.getElementById('auto-next-toggle').checked = isAutoNext;
    updateShuffleBtn();

}

function renderPlaylist() {
    playlistRenderedForLength = state.currentGridVideos.length;
    renderPlaylistWindow();
}

function renderPlaylistWindow(anchorIndex = state.currentIndex) {
    const container = document.getElementById('playlist-content');
    if (!container) return;

    const count = state.currentGridVideos.length;
    if (!count) {
        container.innerHTML = '';
        return;
    }

    const safeAnchor = Math.max(0, Math.min(anchorIndex, count - 1));
    const start = Math.max(0, safeAnchor - PLAYLIST_WINDOW_RADIUS);
    const end = Math.min(count, safeAnchor + PLAYLIST_WINDOW_RADIUS + 1);
    const items = state.currentGridVideos.slice(start, end);

    const previousButton = start > 0
        ? `<button onclick="pagePlaylist(-1, ${start})" class="w-full py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-blue-400 hover:bg-white/5 rounded-lg">↑ Nạp phim trước</button>`
        : '';
    const nextButton = end < count
        ? `<button onclick="pagePlaylist(1, ${end})" class="w-full py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-blue-400 hover:bg-white/5 rounded-lg">Nạp phim tiếp ↓</button>`
        : '';

    container.innerHTML = previousButton + items.map((v, offset) => {
        const i = start + offset;
        return `
        <div class="playlist-item rounded-lg" id="plist-item-${i}" onclick="playVideoFromIndex(${i})">
            <div class="relative w-16 aspect-video rounded overflow-hidden bg-slate-800 shrink-0">
                <img src="${escapeAttr(getThumbnailUrl(v.full_path, v.type))}" class="w-full h-full object-cover" loading="lazy" decoding="async">
                ${v.ext && (v.ext.toLowerCase() === '.ts' || v.ext.toLowerCase() === '.m2ts') ? '<div class="absolute bottom-0 right-0 px-1 bg-red-600 text-[6px] font-bold text-white">TS</div>' : ''}
            </div>
            <div class="playlist-info overflow-hidden">
                <div class="playlist-title text-xs font-medium text-slate-300 truncate">${escapeHtml(v.name)}</div>
                <div class="playlist-meta text-[10px] text-slate-500 flex gap-2">
                    <span>${formatDuration(v.duration)}</span>
                    <span>${formatSize(v.size)}</span>
                </div>
            </div>
            ${i === state.currentIndex ? '<i class="fa-solid fa-chart-simple text-blue-500 text-xs animate-pulse"></i>' : ''}
        </div>`;
    }).join('') + nextButton;

    const activeItem = document.getElementById(`plist-item-${state.currentIndex}`);
    if (activeItem) {
        activeItem.classList.add('active', 'bg-blue-600/10', 'border-blue-500/30');
        activeItem.querySelector('.playlist-title')?.classList.add('text-blue-400');
        requestAnimationFrame(() => {
            activeItem.scrollIntoView({ behavior: 'auto', block: 'center' });
        });
    }
}

function updatePlaylistActiveItem() {
    renderPlaylistWindow();
}

window.pagePlaylist = (direction, boundaryIndex) => {
    const count = state.currentGridVideos.length;
    if (!count) return;
    const jump = PLAYLIST_WINDOW_RADIUS * 2;
    const anchor = direction < 0
        ? Math.max(0, boundaryIndex - jump)
        : Math.min(count - 1, boundaryIndex + PLAYLIST_WINDOW_RADIUS);
    renderPlaylistWindow(anchor);
};

// --- Logic ---

window.togglePlaylist = (force) => {
    const sb = document.getElementById('playlist-sidebar');
    const overlay = document.getElementById('playlist-overlay');
    if (!sb) return;

    const isShow = sb.classList.contains('show');
    const shouldShow = force !== undefined ? force : !isShow;

    if (shouldShow) {
        sb.classList.add('show');
        overlay.classList.remove('hidden');
        setTimeout(() => overlay.classList.remove('opacity-0'), 10);
    } else {
        sb.classList.remove('show');
        overlay.classList.add('opacity-0');
        setTimeout(() => overlay.classList.add('hidden'), 300);
    }
};

window.toggleAutoNext = (el) => {
    isAutoNext = el.checked;
};

window.toggleShuffle = () => {
    isShuffle = !isShuffle;
    updateShuffleBtn();
};

function updateShuffleBtn() {
    const btn = document.getElementById('btn-shuffle');
    if (!btn) return;
    if (isShuffle) {
        btn.classList.add('text-blue-400', 'bg-blue-600/20');
        btn.classList.remove('text-slate-500', 'bg-white/5');
    } else {
        btn.classList.remove('text-blue-400', 'bg-blue-600/20');
        btn.classList.add('text-slate-500', 'bg-white/5');
    }
}

// --- Main Player Logic ---

export function closeVideoModal() {
    clearTimeout(historyRecordTimer);
    historyRecordTimer = null;
    if (state.player) state.player.pause();
    window.togglePlaylist?.(false);

    const modal = document.getElementById('video-modal');
    // Clear any inline drag transform/transition so Tailwind transform classes can take over.
    modal.style.transform = '';
    modal.style.transition = '';
    modal.classList.add('translate-y-full');
    modal.classList.remove('translate-y-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

function getCurrentMedia() {
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
        if (isAutoNext) playNext(true);
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

function loadVideoSource(v) {
    currentRotation = 0;
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

    currentRotation = (currentRotation + 90) % 360;

    if (currentRotation === 90 || currentRotation === 270) {
        // Tính toán scale để không bị crop khi xoay dọc trong container ngang
        const container = video.parentElement;
        const rect = container.getBoundingClientRect();

        // OffsetWidth/Height của video trước khi xoay
        const scale = Math.min(rect.width / video.offsetHeight, rect.height / video.offsetWidth);
        video.style.transform = `rotate(${currentRotation}deg) scale(${scale})`;
    } else {
        video.style.transform = `rotate(${currentRotation}deg) scale(1)`;
    }
};

// --- Navigation ---

function isImageMedia(item) {
    if (!item) return false;
    const lowerPath = (item.full_path || '').toLowerCase();
    return item.type === 'image' || ['.jpg', '.jpeg', '.png', '.webp', '.gif'].some(ext => lowerPath.endsWith(ext));
}

function openMediaAtIndex(idx) {
    const item = state.currentGridVideos[idx];
    if (!item) return;

    const videoModal = document.getElementById('video-modal');
    const imageModal = document.getElementById('image-modal');

    if (isImageMedia(item)) {
        if (videoModal && !videoModal.classList.contains('hidden')) closeVideoModal();
        openImageModal(idx);
    } else {
        if (imageModal && !imageModal.classList.contains('hidden')) closeImageModal();
        openVideoModal(idx);
    }
}

export function playNext(auto = false) {
    const count = state.currentGridVideos.length;
    if (!count) return;

    let nextIdx = -1;
    if (isShuffle) {
        if (count === 1) nextIdx = 0;
        else {
            do {
                nextIdx = Math.floor(Math.random() * count);
            } while (nextIdx === state.currentIndex);
        }
    } else if (state.currentIndex < count - 1) {
        nextIdx = state.currentIndex + 1;
    } else if (auto) {
        nextIdx = 0;
    }

    if (nextIdx !== -1) openMediaAtIndex(nextIdx);
}

export function playPrev() {
    if (state.currentIndex > 0) {
        openMediaAtIndex(state.currentIndex - 1);
    }
}

// Helpers
function formatDuration(sec) {
    if (!sec) return '00:00';
    const min = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${min}:${s < 10 ? '0' + s : s}`;
}

function formatSize(bytes) {
    if (!bytes) return '0 MB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

function renderFallbackUI(container, v, msg) {
    let overlay = container.querySelector('.fallback-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'fallback-overlay absolute inset-0 z-50 bg-slate-900 flex flex-col items-center justify-center space-y-4 p-6 text-center';
        container.appendChild(overlay);
    }
    overlay.style.display = 'flex';
    overlay.innerHTML = `
        <div class="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center mb-2 animate-pulse">
            <i class="fa-solid fa-triangle-exclamation text-4xl text-yellow-500"></i>
        </div>
        <h3 class="text-white font-bold text-lg">${escapeHtml(msg)}</h3>
        <p class="text-slate-400 text-sm max-w-md">File <b>${escapeHtml(v.name)}</b> không hỗ trợ phát trực tiếp trên web.</p>
        <div class="flex gap-3 mt-4">
             <button onclick="playExternal('${escapeInlineJsSingleQuoted(v.full_path)}')" class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-lg shadow-blue-900/50 flex items-center gap-2"><i class="fa-solid fa-external-link-alt"></i> Mở ngoài</button>
             <button onclick="closeVideoModal()" class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold">Đóng</button>
        </div>
    `;
}

// Exports for Window
export function openImageModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image-img');
    const title = document.getElementById('image-modal-title');

    // Reset animation classes if any
    img.classList.remove('opacity-0', 'scale-90', 'translate-x-10', '-translate-x-10');

    title.textContent = v.name;
    img.src = getStreamUrl(v.full_path);

    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('opacity-100'), 10);

    // Add Wheel Event for navigation
    window.addEventListener('wheel', handleImageWheel, { passive: false });
}

export function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('opacity-100');
    setTimeout(() => {
        modal.classList.add('hidden');
        document.getElementById('modal-image-img').src = '';
    }, 300);
    window.removeEventListener('wheel', handleImageWheel);
}

let lastWheelTime = 0;
async function handleImageWheel(e) {
    const modal = document.getElementById('image-modal');
    if (modal.classList.contains('hidden')) return;

    e.preventDefault();
    const now = Date.now();
    if (now - lastWheelTime < 600) return; // Throttling for animation to finish

    const img = document.getElementById('modal-image-img');
    const direction = e.deltaY > 0 ? 1 : -1;

    // Start Exit Animation
    img.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    img.style.opacity = '0';
    img.style.transform = `translateX(${-direction * 50}px) scale(0.95)`;

    setTimeout(() => {
        if (direction > 0) playNext();
        else playPrev();

        // Start Enter Animation (Reset position)
        img.style.transition = 'none';
        img.style.transform = `translateX(${direction * 50}px) scale(0.95)`;

        // Trigger reflow
        img.offsetHeight;

        // Animate in
        img.style.transition = 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
        img.style.opacity = '1';
        img.style.transform = 'translateX(0) scale(1)';
    }, 300);

    lastWheelTime = now;
}

window.closeVideoModal = closeVideoModal;
window.closeImageModal = closeImageModal;
window.playVideoFromIndex = (idx) => {
    openMediaAtIndex(idx);
};
window.playStreamFromIndex = (event, idx) => {
    event.stopPropagation();
    window.playVideoFromIndex(idx);
};

// --- Keyboard Shortcuts ---
window.addEventListener('keydown', (e) => {
    const modal = document.getElementById('video-modal');
    if (modal.classList.contains('hidden')) return;

    // Ignore if typing in an input/textarea
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    if (e.code === 'Space') {
        e.preventDefault();
        if (state.player) state.player.togglePlay();
    } else if (e.code === 'Escape') {
        e.preventDefault();
        closeVideoModal();
        closeImageModal();
    } else if (e.code === 'ArrowRight' || e.code === 'ArrowDown') {
        e.preventDefault();
        playNext();
    } else if (e.code === 'ArrowLeft' || e.code === 'ArrowUp') {
        e.preventDefault();
        playPrev();
    }
});

// Helper to play a video that might not be in the current view's grid (History)
window.playByPath = (path, type = 'video') => {
    // Find video in all cached videos if possible to get context/playlist
    const target = state.allVideos.find(v => v.full_path === path);
    if (target) {
        // If it's in allVideos, we might need to update state.currentGridVideos 
        // to include it so the playlist works. For now, just play it as a single entry.
        const originalGrid = [...state.currentGridVideos];
        if (!originalGrid.find(v => v.full_path === path)) {
            state.currentGridVideos = [target, ...originalGrid];
            openVideoModal(0);
        } else {
            const idx = state.currentGridVideos.findIndex(v => v.full_path === path);
            openVideoModal(idx);
        }
    } else {
        // Fallback or Image?
        if (type === 'image') window.open(getStreamUrl(path), '_blank');
        else {
            // Create a dummy video object to play
            const dummy = { full_path: path, name: path.split(/[\\/]/).pop(), type: 'video' };
            state.currentGridVideos = [dummy];
            openVideoModal(0);
        }
    }
};
window.togglePlayerFavorite = async () => {
    const video = state.currentGridVideos[state.currentIndex];
    if (!video) return;

    const isFavorite = await favoritesService.toggleFavorite(video);
    updatePlayerFavoriteUI(video.full_path);

    const card = document.querySelector(`.movie-card[data-path="${CSS.escape(video.full_path)}"]`);
    const icon = card?.querySelector('button[onclick^="handleFavoriteToggle"] i');
    if (icon) {
        icon.className = `fa-${isFavorite ? 'solid' : 'regular'} fa-heart ${isFavorite ? 'text-red-500' : 'text-white/70 group-hover/heart:text-red-400'} transition`;
    }
};

function updatePlayerFavoriteUI(path) {
    const btn = document.getElementById('player-btn-favorite');
    if (!btn) return;
    const isFav = favoritesService.isFavorite(path);
    btn.innerHTML = `<i class="fa-${isFav ? 'solid' : 'regular'} fa-heart ${isFav ? 'text-red-500' : 'text-white/70'} text-xl"></i>`;
}
