import { state } from './state.js';
import { playerRuntime } from './player_runtime.js';

// --- Navigation ---

function isImageMedia(item) {
    if (!item) return false;
    const lowerPath = (item.full_path || '').toLowerCase();
    return item.type === 'image' || ['.jpg', '.jpeg', '.png', '.webp', '.gif'].some(ext => lowerPath.endsWith(ext));
}

export function openMediaAtIndex(idx) {
    const item = state.currentGridVideos[idx];
    if (!item) return;

    const videoModal = document.getElementById('video-modal');
    const imageModal = document.getElementById('image-modal');

    if (isImageMedia(item)) {
        if (videoModal && !videoModal.classList.contains('hidden')) window.closeVideoModal?.();
        window.openImageModal?.(idx);
    } else {
        if (imageModal && !imageModal.classList.contains('hidden')) window.closeImageModal?.();
        window.openVideoModal?.(idx);
    }
}

export function playNext(auto = false) {
    const count = state.currentGridVideos.length;
    if (!count) return;

    let nextIdx = -1;
    if (playerRuntime.isShuffle) {
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

