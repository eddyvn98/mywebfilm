// static/js/main.js
import { state } from './state.js';
import { checkPinStatus } from './auth.js';
import { renderFolders, applyFilters, restoreScroll } from './grid.js';
import { initGestures } from './gestures.js';
import { startQueuePolling } from './manage_service.js';
import { fetchConfig, fetchVideos, apiAddFolder, apiRemoveFolder } from './api.js';
import { playOnServer } from './api.js';

function syncUIFromState() {
    const typeMap = { 'all': 'TẤT CẢ', 'video': 'VIDEO', 'image': 'ẢNH' };
    const sortMap = {
        'added_newest': 'MỚI CẬP NHẬT',
        'newest': 'FILE MỚI NHẤT',
        'views_desc': 'XEM NHIỀU',
        'name': 'TÊN A-Z'
    };

    const typeLabel = document.getElementById('type-label');
    const categoryLabel = document.getElementById('category-label');
    const sortLabel = document.getElementById('sort-label');

    if (typeLabel) typeLabel.innerText = typeMap[state.filterType] || 'TẤT CẢ';
    if (categoryLabel) categoryLabel.innerText = state.currentCategory === 'all' ? 'THỂ LOẠI' : state.currentCategory.toUpperCase();
    if (sortLabel) sortLabel.innerText = sortMap[state.sortOrder] || 'MỚI CẬP NHẬT';
}

async function loadLibrary() {
    try {
        console.log("PIN Success: Loading Library...");
        state.allVideos = await fetchVideos();
        renderFolders();
        applyFilters();
        restoreScroll();
        initGestures();
        startQueuePolling(); // Check for any ongoing background tasks on load
    } catch (e) {
        console.error("Library load failed:", e);
    }
}

async function init() {
    try {
        const config = await fetchConfig();
        if (config.pin) state.correctPin = config.pin;
        checkPinStatus();
        syncUIFromState();

        const sourceList = document.getElementById('source-list');
        sourceList.innerHTML = (config.video_dirs || []).map(path => `
            <div class="group flex items-center justify-between px-4 py-3 hover:bg-slate-800/40 rounded-lg">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-500/10 rounded-lg"><i class="fa-solid fa-folder text-blue-400"></i></div>
                    <span class="text-slate-300 font-medium text-sm truncate max-w-[150px]" title="${path}">${path}</span>
                </div>
                <button onclick="removeFolder('${path.replace(/\\/g, '\\\\')}')" 
                        class="opacity-0 group-hover:opacity-100 p-2 text-slate-500 hover:text-red-500 transition">
                    <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
            </div>`).join('');

        // If already authenticated, load immediately
        if (sessionStorage.getItem('cinema_authenticated') === 'true') {
            loadLibrary();
        }
    } catch (e) {
        console.error("Init failed:", e);
    }
}

window.loadLibrary = loadLibrary;

// --- UI GLOBALS ---
window.toggleSidebar = () => {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
};

window.refreshLibrary = async () => {
    const btn = document.getElementById('btn-refresh');
    btn.classList.add('animate-spin');
    try {
        await fetch('/api/scan', { method: 'POST' });
        state.allVideos = await fetchVideos();
        renderFolders();
        applyFilters();
        startQueuePolling(); // Start polling in case scan triggered auto-conversion
    } finally {
        setTimeout(() => btn.classList.remove('animate-spin'), 500);
    }
};

window.clearAllCache = async () => {
    if (confirm('Xóa toàn bộ cache (thumbnail/preview)? Thao tác này sẽ làm máy chậm lúc đầu.')) {
        await fetch('/api/clear_cache', { method: 'POST' });
        location.reload();
    }
};

window.addFolder = async () => {
    const input = document.getElementById('new-folder-path');
    const path = input.value.trim();
    if (!path) return;
    const res = await apiAddFolder(path);
    if (res.ok) {
        input.value = '';
        init();
    } else {
        alert("Đường dẫn không hợp lệ hoặc không tồn tại!");
    }
};

window.removeFolder = async (path) => {
    if (confirm(`Xóa nguồn: ${path}?`)) {
        const res = await apiRemoveFolder(path);
        if (res.ok) init();
    }
};

window.toggleBlur = () => {
    const grid = document.getElementById('video-grid');
    const btn = document.getElementById('btn-blur');
    const isBlurred = grid.classList.toggle('poster-blur');

    localStorage.setItem('cinema_poster_blur', isBlurred);
    btn.classList.toggle('blur-btn-active', isBlurred);
    btn.querySelector('i').className = isBlurred ? 'fa-solid fa-eye text-sm' : 'fa-solid fa-eye-slash text-sm';
};

// Apply blur on load if persisted
const initBlur = () => {
    const isBlurred = localStorage.getItem('cinema_poster_blur') === 'true';
    if (isBlurred) {
        document.getElementById('video-grid').classList.add('poster-blur');
        const btn = document.getElementById('btn-blur');
        if (btn) {
            btn.classList.add('blur-btn-active');
            btn.querySelector('i').className = 'fa-solid fa-eye text-sm';
        }
    }
};

// Initial load
init().then(initBlur);
