// static/js/main.js
import { state } from './state.js';
import { escapeHtml, escapeAttr, escapeInlineJsSingleQuoted } from './security.js';
import { historyService } from './history_service.js';
import { favoritesService } from './favorites_service.js';
import { renderFolders, applyFilters, restoreScroll } from './grid.js';
import { initGestures } from './gestures.js';
import { startQueuePolling } from './manage_service.js';
import { fetchConfig, fetchVideos, apiAddFolder, apiRemoveFolder } from './api.js';
import { playOnServer } from './api.js';
import { initSecurityClient } from './security_client.js';
import { runLibraryScan } from './scan_service.js';
import { beginSmartMixVisit } from './smart_mix_service.js';

function syncUIFromState() {
    const typeMap = { 'all': 'TẤT CẢ', 'video': 'VIDEO', 'image': 'ẢNH' };
    const sortMap = {
        'smart_mix': 'GỢI Ý',
        'added_newest': 'MỚI CẬP NHẬT',
        'newest': 'FILE MỚI NHẤT',
        'views_desc': 'XEM NHIỀU',
        'name': 'TÊN A-Z',
        'name_desc': 'TÊN Z-A',
        'duration_desc': 'DÀI NHẤT',
        'duration_asc': 'NGẮN NHẤT',
        'release_desc': 'PHÁT HÀNH MỚI',
        'metadata_desc': 'METADATA MỚI',
        'size_desc': 'DUNG LƯỢNG LỚN',
        'size_asc': 'DUNG LƯỢNG NHỎ'
    };

    const typeLabel = document.getElementById('type-label');
    const categoryLabel = document.getElementById('category-label');
    const sortLabel = document.getElementById('sort-label');

    if (typeLabel) typeLabel.innerText = typeMap[state.filterType] || 'TẤT CẢ';
    if (categoryLabel) categoryLabel.innerText = state.currentCategory === 'all' ? 'THỂ LOẠI' : state.currentCategory.toUpperCase();
    if (sortLabel) sortLabel.innerText = sortMap[state.sortOrder] || 'GỢI Ý';
}

function uniquePaths(paths) {
    const seen = new Set();
    const cleaned = [];
    for (const path of paths || []) {
        const normalized = (path || '').trim();
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        cleaned.push(normalized);
    }
    return cleaned;
}

async function loadLibrary() {
    try {
        console.log("loadLibrary() started...");
        const [videos] = await Promise.all([
            fetchVideos(),
            favoritesService.loadFavorites(),
            historyService.loadHistoryData(),
        ]);
        console.log("fetchVideos() returned:", videos ? videos.length : 'NULL', "items");
        state.allVideos = videos;

        renderFolders();
        applyFilters();
        restoreScroll();
        initGestures();
        startQueuePolling();
    } catch (e) {
        console.error("loadLibrary() FAILED:", e);
    }
}

async function init() {
    try {
        console.log("Initializing App...");
        beginSmartMixVisit();
        const config = await fetchConfig();
        console.log("Config loaded:", config);

        syncUIFromState();
        initSecurityClient();

        const sourceList = document.getElementById('source-list');
        if (!sourceList) {
            console.error("CRITICAL: Element #source-list not found! Sidebar might be missing.");
            return;
        }

        const videoDirs = uniquePaths(config.video_dirs);
        sourceList.innerHTML = videoDirs.map(path => `
            <div class="group flex items-center justify-between gap-2 px-4 py-2 hover:bg-slate-800/40 rounded-lg transition-colors">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                    <div class="p-2 bg-blue-500/10 rounded-lg shrink-0"><i class="fa-solid fa-folder text-blue-400"></i></div>
                    <span class="text-slate-300 font-medium text-sm truncate" title="${escapeAttr(path)}">${escapeHtml(path)}</span>
                </div>
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                     <button onclick="renameFolder('${escapeInlineJsSingleQuoted(path)}')" 
                            class="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-blue-500 hover:bg-blue-500/10 rounded-md transition" title="Đổi tên an toàn (giữ thumbnail)">
                        <i class="fa-solid fa-pen text-xs"></i>
                    </button>
                    <button onclick="removeFolder('${escapeInlineJsSingleQuoted(path)}')" 
                            class="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-red-500 hover:bg-red-500/10 rounded-md transition" title="Xóa nguồn">
                        <i class="fa-solid fa-trash-can text-xs"></i>
                    </button>
                </div>
            </div>`).join('');

        console.log("Source list rendered.");

        // The server only renders this page for an authenticated, unlocked session.
        console.log("Authenticated session, loading library...");
        await loadLibrary();
        fetch('/api/sort/incoming_count').then(r => r.json()).then(d => _updateSortBadge(d.count || 0)).catch(() => {});

        const scheduleBackgroundSort = () => autoSortIncoming({ silent: true });
        if ('requestIdleCallback' in window) {
            window.requestIdleCallback(scheduleBackgroundSort, { timeout: 5000 });
        } else {
            setTimeout(scheduleBackgroundSort, 3000);
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

window.closeSidebarOnMobile = () => {
    if (window.innerWidth >= 768) return;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (!sidebar || !overlay) return;
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
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
        // Step 1: Auto-sort Incoming folders before scanning library
        await autoSortIncoming({ silent: false });

        // Step 2: Rebalance already sorted movies across G -> H -> E
        await autoRebalanceLibrary({ silent: false });

        // Step 3: Run the library scan outside the Waitress request thread,
        // then reload the catalog only after the background job is complete.
        await runLibraryScan();
        state.allVideos = await fetchVideos().catch(e => {
            console.error("Fetch videos failed:", e);
            return state.allVideos;
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

/**
 * autoSortIncoming - Triggers the sort engine for Incoming folders.
 * If silent=true, only runs when Incoming has videos (no UI toast).
 * If silent=false, shows a small toast overlay with progress.
 */
window.autoSortIncoming = async ({ silent = true } = {}) => {
    return runSortJob({ mode: 'incoming', silent });
};

window.autoRebalanceLibrary = async ({ silent = true } = {}) => {
    return runSortJob({ mode: 'rebalance', silent });
};

async function runSortJob({ mode, silent }) {
    try {
        let count = 0;
        if (mode === 'incoming') {
            // Check if there are videos to sort
            const countRes = await fetch('/api/sort/incoming_count').then(r => r.json());
            count = countRes.count || 0;

            if (count === 0) {
                // Update badge to 0
                _updateSortBadge(0);
                return;
            }
        }

        // Show toast if not silent
        const toast = silent ? null : _showSortToast(mode === 'incoming' ? count : 0);
        if (toast && mode === 'rebalance') {
            const title = toast.querySelector('div');
            if (title) title.textContent = 'Đang cân bằng lại kho phim...';
        }

        // Trigger job (non-dry-run)
        const sortRes = await fetch('/api/sort/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dry_run: false, mode })
        }).then(r => r.json());

        if (!sortRes.ok && sortRes.msg !== 'Sort already running') return;

        // Poll until done
        await _pollSortUntilDone(toast);

        // Refresh badge only for Incoming sort
        if (mode === 'incoming') {
            const afterCount = await fetch('/api/sort/incoming_count').then(r => r.json());
            _updateSortBadge(afterCount.count || 0);
        }
    } catch (e) {
        console.warn('[AutoSort] Error:', e);
    }
}

async function _pollSortUntilDone(toast) {
    while (true) {
        await new Promise(r => setTimeout(r, 800));
        const s = await fetch('/api/sort/status').then(r => r.json()).catch(() => ({ status: 'done' }));
        if (toast) _updateSortToast(toast, s);
        if (s.status === 'done' || s.status === 'idle') break;
    }
}

function _updateSortBadge(count) {
    let badge = document.getElementById('sort-incoming-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
    }
}

function _showSortToast(count) {
    let toast = document.getElementById('sort-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'sort-toast';
        toast.style.cssText = [
            'position:fixed', 'bottom:80px', 'left:50%', 'transform:translateX(-50%)',
            'background:rgba(15,15,25,0.95)', 'border:1px solid #7c3aed',
            'border-radius:12px', 'padding:14px 20px', 'z-index:9999',
            'font-size:0.88rem', 'color:#e2e8f0', 'min-width:280px', 'text-align:center',
            'box-shadow:0 4px 30px rgba(124,58,237,0.3)'
        ].join(';');
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<div style="color:#a855f7;font-weight:700;margin-bottom:6px">📦 Đang sắp xếp ${count} video mới...</div>
        <div id="sort-toast-bar" style="background:#1e1e2e;border-radius:999px;height:6px;overflow:hidden">
          <div id="sort-toast-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#7c3aed,#a855f7);transition:width .3s"></div>
        </div>
        <div id="sort-toast-info" style="color:#64748b;font-size:0.78rem;margin-top:6px">Đang khởi động...</div>`;
    toast.style.display = 'block';
    return toast;
}

function _updateSortToast(toast, s) {
    if (!toast) return;
    const fill = document.getElementById('sort-toast-fill');
    const info = document.getElementById('sort-toast-info');
    if (fill) fill.style.width = (s.pct || 0) + '%';
    if (info) {
        if (s.status === 'done') {
            info.textContent = `✅ Xong! Đã sort ${(s.moved||[]).length} phim.`;
            setTimeout(() => { if (toast) toast.style.display = 'none'; }, 3000);
        } else {
            info.textContent = s.current_file ? `📄 ${s.current_file}` : (s.status === 'scanning' ? 'Đang quét...' : `${s.done||0}/${s.total||0}`);
        }
    }
}

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

window.playExternal = (path, type = 'video') => playOnServer(path, type);

// Initial load
init().then(initBlur);

