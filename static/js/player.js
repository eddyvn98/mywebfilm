// static/js/player.js
import { state } from './state.js';
import { getStreamUrl, getThumbnailUrl } from './api.js';
import { historyService } from './history_service.js';
import { favoritesService } from './favorites_service.js';

let isAutoNext = false;
let isShuffle = false;

export function openVideoModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    // Inject UI if missing
    if (!document.getElementById('playlist-sidebar')) {
        injectPlaylistUI();
    }

    const modal = document.getElementById('video-modal');
    modal.classList.remove('hidden');
    void modal.offsetWidth;
    modal.classList.add('translate-y-0');
    modal.classList.remove('translate-y-full');

    // Update Title & Favorite
    const titleEl = document.getElementById('video-modal-title');
    if (titleEl) titleEl.textContent = v.name;
    updatePlayerFavoriteUI(v.full_path);

    // Track History
    historyService.addToHistory(v);

    loadVideoSource(v);
    renderPlaylist();
    updatePlaylistActiveItem();
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

    // Attach Mobile Gesture Zone (Mid-screen swipe)
    const gestureZone = document.createElement('div');
    gestureZone.className = 'absolute top-0 bottom-0 right-12 w-24 z-[100] md:hidden';
    // ^ Right area but not edge. Actually user asked for "swipe from middle". 
    // We'll attach touch listener to the whole modal but filter coordinate.
    modal.addEventListener('touchstart', handleTouchStart, { passive: true });
    modal.addEventListener('touchmove', handleTouchMove, { passive: true });
}

function renderPlaylist() {
    const container = document.getElementById('playlist-content');
    if (!container) return;

    container.innerHTML = state.currentGridVideos.map((v, i) => `
        <div class="playlist-item rounded-lg" id="plist-item-${i}" onclick="playVideoFromIndex(${i})">
            <div class="relative w-16 aspect-video rounded overflow-hidden bg-slate-800 shrink-0">
                <img src="${getThumbnailUrl(v.full_path, v.type)}" class="w-full h-full object-cover" loading="lazy">
                ${v.ext && (v.ext.toLowerCase() === '.ts' || v.ext.toLowerCase() === '.m2ts') ? '<div class="absolute bottom-0 right-0 px-1 bg-red-600 text-[6px] font-bold text-white">TS</div>' : ''}
            </div>
            <div class="playlist-info overflow-hidden">
                <div class="playlist-title text-xs font-medium text-slate-300 truncate">${v.name}</div>
                <div class="playlist-meta text-[10px] text-slate-500 flex gap-2">
                    <span>${formatDuration(v.duration)}</span>
                    <span>${formatSize(v.size)}</span>
                </div>
            </div>
            ${i === state.currentIndex ? '<i class="fa-solid fa-chart-simple text-blue-500 text-xs animate-pulse"></i>' : ''}
        </div>
    `).join('');
}

function updatePlaylistActiveItem() {
    document.querySelectorAll('.playlist-item').forEach(el => {
        el.classList.remove('active', 'bg-blue-600/10', 'border-blue-500/30');
        el.querySelector('.playlist-title').classList.remove('text-blue-400');
    });

    const activeItem = document.getElementById(`plist-item-${state.currentIndex}`);
    if (activeItem) {
        activeItem.classList.add('active', 'bg-blue-600/10', 'border-blue-500/30');
        activeItem.querySelector('.playlist-title').classList.add('text-blue-400');

        // Scroll to active
        setTimeout(() => {
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
    }
}

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
    if (state.player) state.player.pause();
    const modal = document.getElementById('video-modal');
    modal.classList.add('translate-y-full');
    modal.classList.remove('translate-y-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

function loadVideoSource(v) {
    let video = document.getElementById('modal-player');
    if (!video && state.player) video = state.player.media;
    if (!video) return;

    const ext = (v.ext || '').toLowerCase();
    if (ext === '.ts' || ext === '.m2ts') {
        renderFallbackUI(video.parentElement, v, "Trình duyệt không hỗ trợ định dạng này (.TS)");
        return;
    }

    // Reset fallback if needed
    const overlay = video.parentElement.querySelector('.fallback-overlay');
    if (overlay) overlay.style.display = 'none';

    const sourceUrl = getStreamUrl(v.full_path);

    if (state.player) {
        state.player.source = { type: 'video', sources: [{ src: sourceUrl }] };
    } else {
        video.src = sourceUrl;
    }

    const savedTime = localStorage.getItem('resume_' + v.full_path);
    if (savedTime) {
        if (state.player) {
            state.player.once('ready', () => state.player.currentTime = parseFloat(savedTime));
        } else {
            video.currentTime = parseFloat(savedTime);
        }
    }

    if (!state.player) {
        state.player = new Plyr(video, {
            controls: [
                'play-large', 'restart', 'rewind', 'play', 'fast-forward', 'progress',
                'current-time', 'duration', 'mute', 'volume', 'captions', 'settings',
                'pip', 'airplay', 'fullscreen'
            ],
            fullscreen: { container: '#video-modal' }, // Fix: include sidebar in fullscreen
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

        // Add Custom Playlist Toggle to Plyr controls
        // We do this by injecting HTML because Plyr doesn't support custom buttons easily via config
        setTimeout(injectPlyrCustomControls, 500);

        state.player.on('ended', () => {
            if (isAutoNext) playNext(true);
        });

        state.player.on('timeupdate', () => {
            if (state.player && state.player.currentTime > 5) {
                localStorage.setItem('resume_' + v.full_path, state.player.currentTime);
            }
        });

        state.player.on('error', (e) => {
            console.warn("Player error:", e);
            renderFallbackUI(video.parentElement, v, "Không thể giải mã video này trên trình duyệt");
        });
    } else {
        // Ensure custom button is there if player reused
        setTimeout(injectPlyrCustomControls, 500);
    }

    state.player.play().catch(() => { });
}

function injectPlyrCustomControls() {
    const controls = document.querySelector('.plyr__controls');
    if (controls && !document.getElementById('plyr-btn-playlist')) {
        const btn = document.createElement('button');
        btn.id = 'plyr-btn-playlist';
        btn.type = 'button';
        btn.className = 'plyr__control type-custom';
        btn.innerHTML = '<i class="fa-solid fa-list-ul"></i>';
        btn.onclick = () => window.togglePlaylist();

        // Insert before fullscreen
        const fsBtn = controls.querySelector('[data-plyr="fullscreen"]');
        if (fsBtn) controls.insertBefore(btn, fsBtn);
        else controls.appendChild(btn);
    }
}

// --- Gestures ---
let touchStartX = 0;
let touchStartY = 0;

function handleTouchStart(e) {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
}

function handleTouchMove(e) {
    // Basic swipe detection
    // User wants "Swipe from right to left" but "Not from edge"
    // And "Mid screen"

    // We handle 'touchend' normally, but user might want responsive drag.
    // Let's stick to simple swipe detection on End for now for simplicity & stability.
}

window.addEventListener('touchend', (e) => {
    // Only if modal is open
    const modal = document.getElementById('video-modal');
    if (modal.classList.contains('hidden')) return;

    const touchEndX = e.changedTouches[0].screenX;
    const touchEndY = e.changedTouches[0].screenY;

    const screenW = window.innerWidth;

    // Check constraints
    // 1. Not from edge (e.g. < 20px or > width - 20px)
    // User said: "quẹt từ phải qua trái, ko để quẹt từ cạnh" -> Swipe Left to open sidebar
    // So StartX should be < ScreenWidth - 30px (Not right edge)
    // AND StartX > 40px (Not left edge, though swipe left implies starting right)

    const isEdge = touchStartX < 40 || touchStartX > (screenW - 20);

    // 2. Swipe Left Strength
    const deltaX = touchEndX - touchStartX;
    const deltaY = touchEndY - touchStartY;

    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 60 && !isEdge) {
        // Horizontal Swipe
        if (deltaX < 0) {
            // Swipe Left -> Open Playlist
            togglePlaylist(true);
        } else {
            // Swipe Right -> Close Playlist
            togglePlaylist(false);
        }
    }
}, { passive: true });


// --- Nav ---

export function playNext(auto = false) {
    let nextIdx = -1;

    if (isShuffle) {
        // Simple random calc
        nextIdx = Math.floor(Math.random() * state.currentGridVideos.length);
    } else {
        if (state.currentIndex < state.currentGridVideos.length - 1) {
            nextIdx = state.currentIndex + 1;
        } else if (auto) {
            // Loop back to start if auto next? Or stop.
            // Let's stop to be safe, or loop if user requested. Standard is stop or loop.
            // We'll loop for continuous 'Flow'.
            nextIdx = 0;
        }
    }

    if (nextIdx !== -1) {
        const next = state.currentGridVideos[nextIdx];
        if (next.type === 'image') {
            // If auto next hits an image, skip it or stop?
            // Skip recursively
            state.currentIndex = nextIdx; // Update so recursive call moves forward
            playNext(auto);
        } else {
            openVideoModal(nextIdx);
        }
    }
}

export function playPrev() {
    if (state.currentIndex > 0) {
        state.currentIndex--;
        const prev = state.currentGridVideos[state.currentIndex];
        if (prev.type === 'image') playPrev();
        else openVideoModal(state.currentIndex);
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
        <h3 class="text-white font-bold text-lg">${msg}</h3>
        <p class="text-slate-400 text-sm max-w-md">File <b>${v.name}</b> không hỗ trợ phát trực tiếp trên web.</p>
        <div class="flex gap-3 mt-4">
             <button onclick="playExternal('${v.full_path.replace(/\\/g, '\\\\')}')" class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-lg shadow-blue-900/50 flex items-center gap-2"><i class="fa-solid fa-external-link-alt"></i> Mở ngoài</button>
             <button onclick="closeVideoModal()" class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold">Đóng</button>
        </div>
    `;
}

// Exports for Window
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

    await favoritesService.toggleFavorite(video);
    updatePlayerFavoriteUI(video.full_path);

    // Also refresh grid if visible behind
    const { renderGrid } = await import('./render_service.js');
    renderGrid(state.currentGridVideos, false, false);
};

function updatePlayerFavoriteUI(path) {
    const btn = document.getElementById('player-btn-favorite');
    if (!btn) return;
    const isFav = favoritesService.isFavorite(path);
    btn.innerHTML = `<i class="fa-${isFav ? 'solid' : 'regular'} fa-heart ${isFav ? 'text-red-500' : 'text-white/70'} text-xl"></i>`;
}
