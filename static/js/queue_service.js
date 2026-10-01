// static/js/queue_service.js
import { state } from './state.js';
import { apiAddQueue, apiGetQueueStatus, apiClearQueue, apiProcessConvert } from './api.js';
import { cancelSelection } from './selection_service.js';
import { escapeHtml } from './security.js';

let queuePollInterval = null;

export async function processHighlight(e, index) {
    if (e && e.stopPropagation) e.stopPropagation();
    let paths = [];
    if (typeof index === 'number') {
        const v = state.currentGridVideos[index];
        if (v) paths = [v.full_path];
    } else if (state.selectedPaths && state.selectedPaths.length > 0) {
        paths = [...state.selectedPaths];
    }

    if (paths.length === 0) return;

    const msg = paths.length === 1
        ? `Tạo highlight và xóa video gốc sau khi kiểm tra output thành công?`
        : `Tạo highlight cho ${paths.length} file và xóa từng video gốc sau khi output tương ứng được kiểm tra thành công?`;
    if (!confirm(msg)) return;

    const btn = e?.target?.closest('button') || document.querySelector('button[onclick^="processHighlight"]');
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang thêm...'; btn.disabled = true; }

    try {
        const res = await apiAddQueue(paths);
        if (res.status === 'ok') {
            cancelSelection();
            startQueuePolling();
        }
        else alert("Lỗi server: " + (res.msg || "Không thể thêm vào hàng đợi"));
    } catch (err) {
        alert("Lỗi kết nối:\n" + err.message);
    }
    finally { if (btn) { btn.innerHTML = '<i class="fa-solid fa-scissors"></i> Cắt Highlight'; btn.disabled = false; } }
}

export async function processConvert(e, index) {
    if (e && e.stopPropagation) e.stopPropagation();
    let paths = [];
    if (typeof index === 'number') {
        const v = state.currentGridVideos[index];
        if (v) paths = [v.full_path];
    } else if (state.selectedPaths && state.selectedPaths.length > 0) {
        paths = [...state.selectedPaths];
    }

    if (paths.length === 0) {
        alert("Chưa chọn file nào!");
        return;
    }

    const msg = paths.length === 1 ? `Convert file này sang MP4 (giữ nguyên gốc)?` : `Convert ${paths.length} file sang MP4?`;
    if (!confirm(msg)) return;

    const btn = e?.target?.closest('button') || document.querySelector('button[onclick^="processConvert"]');
    const originalText = btn ? btn.innerHTML : '';
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi...'; btn.disabled = true; }

    try {
        const res = await apiProcessConvert(paths);
        if (res.status === 'ok') {
            cancelSelection();
            startQueuePolling();
        } else {
            alert("Lỗi từ Server: " + (res.msg || "Unknown error"));
        }
    } catch (err) {
        alert("Lỗi Exception: " + err.message);
    } finally {
        if (btn) { btn.innerHTML = originalText || '<i class="fa-solid fa-file-video"></i> Convert MP4'; btn.disabled = false; }
    }
}

export function startQueuePolling() {
    if (queuePollInterval) return;
    updateQueueUI();
    queuePollInterval = setInterval(updateQueueUI, 3000);
}

export async function updateQueueUI() {
    try {
        const status = await apiGetQueueStatus();
        let overlay = document.getElementById('queue-status-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'queue-status-overlay';
            overlay.className = 'fixed top-20 right-6 z-[100] bg-slate-900/90 border border-white/10 rounded-2xl p-4 shadow-2xl backdrop-blur-md w-72 transition-all transform translate-x-80';
            document.body.appendChild(overlay);
            setTimeout(() => overlay.classList.remove('translate-x-80'), 100);
        }
        const activeItem = status.items.find(i => i.status === 'processing');
        const pendingCount = status.items.filter(i => i.status === 'pending').length;
        const completedCount = status.items.filter(i => i.status === 'completed').length;
        const failedCount = status.items.filter(i => i.status === 'failed').length;

        state.queuedPaths = status.items
            .filter(i => i.status === 'pending' || i.status === 'processing')
            .map(i => i.path);

        if (status.items.length === 0 || (status.active_count === 0 && completedCount + failedCount === 0)) {
            overlay.classList.add('translate-x-80');
            setTimeout(() => overlay.remove(), 500);
            if (queuePollInterval) {
                clearInterval(queuePollInterval);
                queuePollInterval = null;
            }
            return;
        }

        const currentType = activeItem ? (activeItem.type === 'convert' ? 'Chuyển đổi' : 'Highlight') : 'Hàng đợi';

        overlay.innerHTML = `<div class="flex items-center justify-between mb-3">
            <h4 class="text-white font-black text-[10px] uppercase tracking-wider">${currentType}</h4>
            ${status.active_count === 0 ? `<button onclick="clearCompletedQueue()" class="text-blue-400 text-[9px] font-bold hover:underline">Xong</button>` : ''}
        </div>
        ${activeItem ? `<div class="bg-blue-600/20 rounded-xl p-3 mb-3 border border-blue-500/30">
            <div class="flex items-center gap-2 mb-1">
                <i class="fa-solid ${activeItem.type === 'convert' ? 'fa-video' : 'fa-scissors'} text-blue-400 text-[10px]"></i>
                <span class="text-white text-[10px] font-bold truncate">${escapeHtml(activeItem.name)}</span>
            </div>
            <div class="h-1 bg-white/10 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 animate-pulse w-2/3"></div>
            </div>
        </div>` : ''}
        <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-white/5 rounded-lg py-2"><div class="text-slate-400 text-[8px] uppercase font-bold">Chờ</div><div class="text-white text-xs font-black">${pendingCount}</div></div>
            <div class="bg-green-500/10 rounded-lg py-2"><div class="text-green-400 text-[8px] uppercase font-bold">Xong</div><div class="text-white text-xs font-black">${completedCount}</div></div>
            <div class="bg-red-500/10 rounded-lg py-2"><div class="text-red-400 text-[8px] uppercase font-bold">Lỗi</div><div class="text-white text-xs font-black">${failedCount}</div></div>
        </div>`;

        if (completedCount > 0 && status.active_count === 0 && !overlay.dataset.refreshed) {
            window.refreshLibrary();
            overlay.dataset.refreshed = "true";
        }
    } catch (e) {
        console.error("Queue poll error:", e);
    }
}

export async function clearCompletedQueue() {
    await apiClearQueue();
    updateQueueUI();
}
