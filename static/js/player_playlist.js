import { state } from './state.js';
import { escapeHtml, escapeAttr } from './security.js';
import { getThumbnailUrl } from './api.js';
import { playerRuntime } from './player_runtime.js';

const PLAYLIST_WINDOW_RADIUS = 40;
let playlistRenderedForLength = -1;

export function ensureSinglePlaylistUI() {
    const modal = document.getElementById('video-modal');
    if (!modal) return;

    const sidebars = [...document.querySelectorAll('#playlist-sidebar')];
    const overlays = [...document.querySelectorAll('#playlist-overlay')];
    sidebars.slice(1).forEach(el => el.remove());
    overlays.slice(1).forEach(el => el.remove());
    if (sidebars[0] && overlays[0]) return;

    sidebars.forEach(el => el.remove());
    overlays.forEach(el => el.remove());
    injectPlaylistUI();
}

function injectPlaylistUI() {
    const modal = document.getElementById('video-modal');
    if (!modal) return;

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
    document.getElementById('auto-next-toggle').checked = playerRuntime.isAutoNext;
    updateShuffleBtn();

}

export function renderPlaylist() {
    playlistRenderedForLength = state.currentGridVideos.length;
    renderPlaylistWindow();
}

export function renderPlaylistWindow(anchorIndex = state.currentIndex) {
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
        const sb = document.getElementById('playlist-sidebar');
        if (sb && sb.classList.contains('show')) {
            container.scrollTop = Math.max(
                0,
                activeItem.offsetTop
                - (container.clientHeight / 2)
                + (activeItem.clientHeight / 2)
            );
        }
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
        ? Math.max(0, boundaryIndex - PLAYLIST_WINDOW_RADIUS - 1)
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
        sb.setAttribute('aria-hidden', 'false');
        overlay?.classList.remove('hidden');
        setTimeout(() => overlay?.classList.remove('opacity-0'), 10);
        const activeItem = document.getElementById(`plist-item-${state.currentIndex}`);
        const container = document.getElementById('playlist-content');
        if (container && activeItem) {
            container.scrollTop = Math.max(
                0,
                activeItem.offsetTop
                - (container.clientHeight / 2)
                + (activeItem.clientHeight / 2)
            );
        }
    } else {
        sb.classList.remove('show');
        sb.setAttribute('aria-hidden', 'true');
        overlay?.classList.add('opacity-0');
        setTimeout(() => {
            if (!sb.classList.contains('show')) overlay?.classList.add('hidden');
        }, 300);
    }
};

window.toggleAutoNext = (el) => {
    playerRuntime.isAutoNext = el.checked;
};

window.toggleShuffle = () => {
    playerRuntime.isShuffle = !playerRuntime.isShuffle;
    updateShuffleBtn();
};

function updateShuffleBtn() {
    const btn = document.getElementById('btn-shuffle');
    if (!btn) return;
    if (playerRuntime.isShuffle) {
        btn.classList.add('text-blue-400', 'bg-blue-600/20');
        btn.classList.remove('text-slate-500', 'bg-white/5');
    } else {
        btn.classList.remove('text-blue-400', 'bg-blue-600/20');
        btn.classList.add('text-slate-500', 'bg-white/5');
    }
}


