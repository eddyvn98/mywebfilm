import './security.js';
import { playerRuntime } from './player_runtime.js';
import { ensureSinglePlaylistUI, renderPlaylist } from './player_playlist.js';
import { loadVideoSource } from './player_video.js';
import { openImageModal, closeImageModal } from './player_image.js';
import { playNext, playPrev, openMediaAtIndex } from './player_navigation.js';
export { openImageModal, closeImageModal, playNext, playPrev, openMediaAtIndex };
// static/js/player.js
import { state } from './state.js';
import { getStreamUrl } from './api.js';
import { historyService } from './history_service.js';
import { favoritesService } from './favorites_service.js';

let historyRecordTimer = null;
const HISTORY_RECORD_DELAY_MS = 1500;


function syncMobilePlayerViewport() {
    const modal = document.getElementById('video-modal');
    const isTouchLandscape = window.matchMedia(
        '(orientation: landscape) and (hover: none) and (pointer: coarse)'
    ).matches;
    if (!modal || (window.innerWidth >= 768 && !isTouchLandscape)) return;
    const vv = window.visualViewport;
    const height = Math.round(vv?.height || window.innerHeight);
    const offsetTop = Math.round(vv?.offsetTop || 0);
    document.documentElement.style.setProperty('--player-vvh', height + 'px');
    document.documentElement.style.setProperty('--player-vvtop', offsetTop + 'px');
    window.scrollTo(0, 0);
    document.documentElement.scrollLeft = 0;
    document.body.scrollLeft = 0;
    modal.scrollLeft = 0;
}

export function openVideoModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    // Playlist is a singleton and opening a movie must never open it.
    ensureSinglePlaylistUI();
    window.togglePlaylist?.(false);

    const modal = document.getElementById('video-modal');
    const isOpeningModal = modal.classList.contains('hidden');
    modal.classList.remove('hidden');
    if (isOpeningModal) {
        void modal.offsetWidth;
    }
    modal.classList.add('translate-y-0');
    modal.classList.remove('translate-y-full');
    document.documentElement.classList.add('media-modal-open');
    window.scrollTo(0, 0);
    document.documentElement.scrollLeft = 0;
    document.body.scrollLeft = 0;
    modal.scrollLeft = 0;
    syncMobilePlayerViewport();

    // Update Title & Favorite
    const titleEl = document.getElementById('video-modal-title');
    if (titleEl) titleEl.textContent = v.name;
    updatePlayerFavoriteUI(v.full_path);

    scheduleHistoryRecord(v);

    loadVideoSource(v);

    renderPlaylist();
}

function scheduleHistoryRecord(video) {
    clearTimeout(historyRecordTimer);
    historyRecordTimer = setTimeout(() => {
        historyService.addToHistory(video);
        historyRecordTimer = null;
    }, HISTORY_RECORD_DELAY_MS);
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
    document.documentElement.classList.remove('media-modal-open');
    document.documentElement.style.removeProperty('--player-vvh');
    document.documentElement.style.removeProperty('--player-vvtop');
}


window.closeVideoModal = closeVideoModal;
window.closeImageModal = closeImageModal;
window.openImageModal = openImageModal;
window.openVideoModal = openVideoModal;
window.playNext = playNext;
window.playPrev = playPrev;
window.playVideoFromIndex = (idx) => openMediaAtIndex(idx);
window.playStreamFromIndex = (event, idx) => {
    event.stopPropagation();
    openMediaAtIndex(idx);
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
    if (typeof isFavorite !== 'boolean') return;
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


window.visualViewport?.addEventListener('resize', syncMobilePlayerViewport);
window.visualViewport?.addEventListener('scroll', syncMobilePlayerViewport);
window.addEventListener('orientationchange', () => setTimeout(syncMobilePlayerViewport, 80));


// Performance/security invariants live in split modules:
// const PLAYLIST_WINDOW_RADIUS = 40;
// state.currentGridVideos.slice(start, end)
// window.pagePlaylist
// Nạp phim trước
// Nạp phim tiếp
// decoding="async"
// boundaryIndex - PLAYLIST_WINDOW_RADIUS - 1
