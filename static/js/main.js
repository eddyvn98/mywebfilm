// static/js/main.js
import { state } from './state.js';
import { historyService } from './history_service.js';
import { favoritesService } from './favorites_service.js';
import { checkPinStatus } from './auth.js';
import { renderGrid, renderFolders, applyFilters, restoreScroll } from './grid.js';
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
        'name': 'TÊN A-Z',
        'name_desc': 'TÊN Z-A',
        'duration_desc': 'DÀI NHẤT',
        'duration_asc': 'NGẮN NHẤT',
        'size_desc': 'DUNG LƯỢNG LỚN',
        'size_asc': 'DUNG LƯỢNG NHỎ'
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
        console.log("loadLibrary() started...");
        const videos = await fetchVideos();
        console.log("fetchVideos() returned:", videos ? videos.length : 'NULL', "items");
        state.allVideos = videos;
        renderFolders();
        renderGrid(videos);
        applyFilters();
        restoreScroll();
        initGestures();
        favoritesService.loadFavorites();
        startQueuePolling();
    } catch (e) {
        console.error("loadLibrary() FAILED:", e);
    }
}

async function init() {
    try {
        console.log("Initializing App...");
        const config = await fetchConfig();
        console.log("Config loaded:", config);

        if (config.pin) state.correctPin = config.pin;
        checkPinStatus();
        syncUIFromState();

        const sourceList = document.getElementById('source-list');
        if (!sourceList) {
            console.error("CRITICAL: Element #source-list not found! Sidebar might be missing.");
            return;
        }

        sourceList.innerHTML = (config.video_dirs || []).map(path => `
            <div class="group flex items-center justify-between gap-2 px-4 py-2 hover:bg-slate-800/40 rounded-lg transition-colors">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                    <div class="p-2 bg-blue-500/10 rounded-lg shrink-0"><i class="fa-solid fa-folder text-blue-400"></i></div>
                    <span class="text-slate-300 font-medium text-sm truncate" title="${path}">${path}</span>
                </div>
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                     <button onclick="renameFolder('${path.replace(/\\/g, '\\\\')}')" 
                            class="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-blue-500 hover:bg-blue-500/10 rounded-md transition" title="Đổi tên an toàn (giữ thumbnail)">
                        <i class="fa-solid fa-pen text-xs"></i>
                    </button>
                    <button onclick="removeFolder('${path.replace(/\\/g, '\\\\')}')" 
                            class="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-red-500 hover:bg-red-500/10 rounded-md transition" title="Xóa nguồn">
                        <i class="fa-solid fa-trash-can text-xs"></i>
                    </button>
                </div>
            </div>`).join('');

        console.log("Source list rendered.");

        // If already authenticated, load immediately
        if (sessionStorage.getItem('cinema_authenticated') === 'true') {
            console.log("Already authenticated, loading library...");
            loadLibrary();
        }
    } catch (e) {
        console.error("Init failed with error:", e);
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

window.toggleSection = (id, btn) => {
    const el = document.getElementById(id);
    const icon = btn.querySelector('i');
    // Check if currently collapsed based on max-height
    // If max-height is 0px, it is collapsed. 
    // If max-height is none or >0, it is expanded.

    const isCollapsed = el.style.maxHeight === '0px';

    if (isCollapsed) {
        // EXPAND
        el.classList.remove('hidden'); // Just in case
        el.style.maxHeight = el.scrollHeight + "px";
        icon.style.transform = 'rotate(0deg)';
        el.style.opacity = '1';

        // Cleanup after transition
        setTimeout(() => {
            if (el.style.maxHeight !== '0px') {
                el.style.maxHeight = 'none';
            }
        }, 300);
    } else {
        // COLLAPSE
        // Set specific height first to animate FROM
        el.style.maxHeight = el.scrollHeight + "px";
        el.offsetHeight; // Force reflow

        el.style.maxHeight = "0px";
        icon.style.transform = 'rotate(-90deg)';
        el.style.opacity = '0.5';
    }
};

window.refreshLibrary = async () => {
    const btn = document.getElementById('btn-refresh');
    if (!btn) return;
    btn.classList.add('animate-spin');
    try {
        // Use a small timeout for scan so it doesn't hang the UI too long
        // If it fails with "Failed to fetch", it's likely the server is restarting
        await fetch('/api/scan', { method: 'POST' }).catch(e => console.warn("Scan fetch failed (server restarting?):", e));
        state.allVideos = await fetchVideos().catch(e => {
            console.error("Fetch videos failed:", e);
            return state.allVideos; // Fallback to current state
        });
        renderFolders();
        applyFilters();
        startQueuePolling();
    } catch (err) {
        console.error("refreshLibrary total error:", err);
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

window.renameFolder = async (path) => {
    const currentName = path.split('\\').pop().split('/').pop();
    const newName = prompt("Nhập tên mới cho thư mục (Hệ thống sẽ tự cập nhật thumbnail):", currentName);

    if (newName && newName !== currentName) {
        try {
            const { apiRename } = await import('./api.js');
            const res = await apiRename(path, newName);
            if (res.status === 'ok') {
                alert("Đổi tên thành công!");
                location.reload(); // Reload to refresh all paths
            } else {
                alert("Lỗi: " + (res.msg || "Không xác định"));
            }
        } catch (e) {
            alert("Lỗi kết nối: " + e.message);
        }
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
