// static/js/manage_service.js
import { state } from './state.js';
import { deleteFile, apiRename, openExplorer } from './api.js';
import { applyFilters } from './filter_service.js';
import { escapeAttr } from './security.js';

// Import from sub-services
import * as selection from './selection_service.js';
import * as queue from './queue_service.js';
import * as aiMgmt from './ai_mgmt_service.js';
import * as mgmtUi from './mgmt_ui_service.js';

// Rename logic (remains here as it's small)
export function openRenameModal(e, index) {
    e.stopPropagation(); state.renamingIndex = index;
    const v = state.currentGridVideos[index];
    const modal = document.getElementById('rename-modal');
    const input = document.getElementById('rename-input');
    input.value = v.name; modal.classList.remove('hidden'); input.focus(); input.select();
}

export function closeRenameModal() { document.getElementById('rename-modal').classList.add('hidden'); state.renamingIndex = null; }

export async function confirmRename() {
    const newName = document.getElementById('rename-input').value.trim();
    if (!newName || state.renamingIndex === null) return;
    const v = state.currentGridVideos[state.renamingIndex];
    const res = await apiRename(v.full_path, newName);
    if (res.status === 'ok') {
        const oldPath = v.full_path; v.full_path = res.new_path; v.name = newName;
        const globalV = state.allVideos.find(x => x.full_path === oldPath);
        if (globalV) { globalV.full_path = res.new_path; globalV.name = newName; }
        closeRenameModal(); applyFilters(true);
    } else { alert(res.msg || 'Lỗi'); }
}

// Misc UI helpers
export function filterByFolder(folder) { state.currentFolder = folder; window.renderFolders(); applyFilters(); }

const previewTimers = new WeakMap();
let activePreviewCard = null;

function clearPreview(el) {
    const timer = previewTimers.get(el);
    if (timer) {
        clearTimeout(timer);
        previewTimers.delete(el);
    }
    const container = el?.querySelector('.preview-container');
    if (container) container.replaceChildren();
    if (activePreviewCard === el) activePreviewCard = null;
}

export function handlePreview(el, active) {
    const url = el.getAttribute('data-preview-url');
    if (!url) return;

    if (!active) {
        clearPreview(el);
        return;
    }

    if (window.matchMedia && !window.matchMedia('(hover: hover)').matches) return;

    clearPreview(el);
    const timer = setTimeout(() => {
        if (!el.isConnected) return;

        if (activePreviewCard && activePreviewCard !== el) {
            clearPreview(activePreviewCard);
        }

        let container = el.querySelector('.preview-container');
        if (!container) {
            const poster = el.querySelector('.poster-content');
            if (!poster) return;
            container = document.createElement('div');
            container.className = 'preview-container absolute inset-0 z-[5] pointer-events-none';
            poster.appendChild(container);
        }

        container.innerHTML = `<video class="preview-video w-full h-full object-cover" muted loop playsinline autoplay preload="metadata"><source src="${escapeAttr(url)}" type="video/mp4"></video>`;
        activePreviewCard = el;
        previewTimers.delete(el);
    }, 450);
    previewTimers.set(el, timer);
}

export function showInfo(e, index) {
    e?.stopPropagation();
    const v = state.currentGridVideos[index];
    if (!v) return;

    state.infoIndex = index;
    const modal = document.getElementById('movie-info-modal');
    if (!modal) return;

    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? '—';
    };

    const duration = Number(v.duration || 0);
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = Math.floor(duration % 60);
    const durationText = duration > 0
        ? (hours > 0
            ? `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
            : `${minutes}:${String(seconds).padStart(2, '0')}`)
        : '—';

    const addedDate = v.date_added
        ? new Date(v.date_added * 1000).toLocaleString('vi-VN')
        : '—';

    setText('movie-info-title', v.name);
    setText('movie-info-path', v.full_path);
    setText('movie-info-folder', v.folder || 'Gốc');
    setText('movie-info-type', v.type === 'image' ? 'Ảnh' : 'Video');
    setText('movie-info-ext', (v.ext || '—').replace('.', '').toUpperCase());
    setText('movie-info-size', v.size_fmt || '—');
    setText('movie-info-duration', durationText);
    setText('movie-info-views', String(v.views || 0));
    setText('movie-info-added', addedDate);

    const categoryBox = document.getElementById('movie-info-categories');
    if (categoryBox) {
        categoryBox.replaceChildren();
        const categories = v.categories || [];
        if (!categories.length) {
            const empty = document.createElement('span');
            empty.className = 'text-slate-500 text-xs';
            empty.textContent = 'Chưa có metadata phân loại';
            categoryBox.appendChild(empty);
        } else {
            categories.forEach(category => {
                const chip = document.createElement('span');
                chip.className = 'movie-info-chip';
                chip.textContent = category;
                categoryBox.appendChild(chip);
            });
        }
    }

    const explorerBtn = document.getElementById('movie-info-explorer-btn');
    if (explorerBtn) {
        explorerBtn.disabled = Boolean(v.is_offline);
        explorerBtn.classList.toggle('opacity-40', Boolean(v.is_offline));
        explorerBtn.classList.toggle('cursor-not-allowed', Boolean(v.is_offline));
    }

    modal.classList.remove('hidden');
    requestAnimationFrame(() => modal.classList.add('movie-info-open'));
}

export function closeMovieInfo() {
    const modal = document.getElementById('movie-info-modal');
    if (!modal) return;
    modal.classList.remove('movie-info-open');
    setTimeout(() => modal.classList.add('hidden'), 180);
    state.infoIndex = null;
}

export async function copyMoviePath() {
    const v = state.currentGridVideos[state.infoIndex];
    if (!v?.full_path) return;

    try {
        await navigator.clipboard.writeText(v.full_path);
    } catch (_) {
        const area = document.createElement('textarea');
        area.value = v.full_path;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
    }

    const btn = document.getElementById('movie-info-copy-btn');
    if (btn) {
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i><span>Đã copy</span>';
        setTimeout(() => { btn.innerHTML = old; }, 1400);
    }
}

export async function openMovieInExplorer() {
    const v = state.currentGridVideos[state.infoIndex];
    if (!v?.full_path || v.is_offline) return;

    const btn = document.getElementById('movie-info-explorer-btn');
    if (btn) btn.disabled = true;

    try {
        const response = await openExplorer(v.full_path);
        let data = {};
        try { data = await response.json(); } catch (_) {}

        if (!response.ok || data.status === 'err') {
            alert(data.msg || 'Không thể mở Explorer. Tính năng này chỉ hoạt động khi truy cập trực tiếp localhost trên máy Windows chứa file.');
        }
    } catch (error) {
        alert('Không thể mở Explorer: ' + error.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

export async function deleteItem(e, index) {
    e.stopPropagation();
    const v = state.currentGridVideos[index];
    if (confirm('Xóa vĩnh viễn?')) {
        const res = await deleteFile(v.full_path);
        if (res.ok) { state.allVideos = state.allVideos.filter(item => item.full_path !== v.full_path); applyFilters(true); }
    }
}

// Re-export constants and functions from sub-services for named imports
export const { toggleManageMode, handleCardClick, toggleSelection, updateSelectionUI, cancelSelection, bulkDelete, bulkMove, selectAll, handleMouseEnter } = selection;
export const { processHighlight, processConvert, startQueuePolling, updateQueueUI, clearCompletedQueue } = queue;

// Re-expose wrapped functions for Management Studio
export function runAiAnalyzeMgmt() {
    return aiMgmt.runAiAnalyzeMgmt(mgmtUi.mgmtListVisible);
}

export function finalizeMetadata() {
    return aiMgmt.finalizeMetadata(mgmtUi.mgmtListVisible, {
        onSuccess: () => {
            mgmtUi.renderMgmtList();
            mgmtUi.updateMgmtCount();
            document.getElementById('mgmt-editor-content').classList.add('hidden');
            document.getElementById('mgmt-editor-empty').classList.remove('hidden');
            window.refreshLibrary();
        }
    });
}

// Global exposure for HTML compatibility
window.openAiLab = mgmtUi.openAiLab;
window.closeAiLab = mgmtUi.closeAiLab;
window.loadUnverifiedList = mgmtUi.loadUnverifiedList;
window.selectFileForMgmt = mgmtUi.selectFileForMgmt;
window.runAiAnalyzeMgmt = runAiAnalyzeMgmt;
window.parseJsonMetadata = aiMgmt.parseJsonMetadata;
window.finalizeMetadata = finalizeMetadata;
window.processConvert = queue.processConvert;
window.processHighlight = queue.processHighlight;
window.clearCompletedQueue = queue.clearCompletedQueue;
window.bulkMove = selection.bulkMove;
window.bulkDelete = selection.bulkDelete;
window.toggleSelection = selection.toggleSelection;
window.cancelSelection = selection.cancelSelection;
window.toggleManageMode = selection.toggleManageMode;
window.handleCardClick = selection.handleCardClick;
window.showInfo = showInfo;
window.closeMovieInfo = closeMovieInfo;
window.copyMoviePath = copyMoviePath;
window.openMovieInExplorer = openMovieInExplorer;
window.deleteItem = deleteItem;
window.selectAll = selection.selectAll;
window.handleMouseEnter = selection.handleMouseEnter;
window.toggleActorTag = mgmtUi.toggleActorTag;
window.toggleGenreTag = mgmtUi.toggleGenreTag;
window.uploadActorImage = aiMgmt.uploadActorImage;
window.saveScrapperCookies = aiMgmt.saveScrapperCookies;
window.setStudio = (val) => {
    document.getElementById('mgmt-studio').value = val;
    mgmtUi.renderMgmtSidebars();
};

// --- Action Sheet Logic (Mobile/Global Menus) ---
window.openActionSheet = (id) => {
    // Close others first
    document.querySelectorAll('.action-sheet').forEach(el => {
        el.classList.remove('active');
        el.style.transform = 'translateY(100%)';
    });

    const sheet = document.getElementById(id);
    const overlay = document.getElementById('action-sheet-overlay');

    if (sheet && overlay) {
        overlay.classList.remove('hidden');
        // Small delay to allow display:block to apply before opacity transition
        requestAnimationFrame(() => {
            overlay.classList.remove('opacity-0');
            sheet.classList.add('active');
            sheet.style.transform = 'translateY(0)';
        });
    }
};

window.closeAllActionSheets = () => {
    const sheets = document.querySelectorAll('.action-sheet');
    const overlay = document.getElementById('action-sheet-overlay');

    sheets.forEach(el => {
        el.classList.remove('active');
        el.style.transform = 'translateY(100%)';
    });

    if (overlay) {
        overlay.classList.add('opacity-0');
        setTimeout(() => {
            overlay.classList.add('hidden');
        }, 300);
    }
};

// Event listeners for UI updates
document.getElementById('mgmt-actors')?.addEventListener('input', mgmtUi.renderMgmtSidebars);
document.getElementById('mgmt-genres')?.addEventListener('input', mgmtUi.renderMgmtSidebars);
document.getElementById('mgmt-search')?.addEventListener('input', () => {
    mgmtUi.renderMgmtList();
    mgmtUi.updateMgmtCount();
});
