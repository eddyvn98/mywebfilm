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
             <button onclick="window.closeVideoModal?.()" class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold">Đóng</button>
        </div>
    `;
}

// Exports for Window

