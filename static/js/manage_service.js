// static/js/manage_service.js
import { state } from './state.js';
import { deleteFile, apiRename } from './api.js';
import { applyFilters } from './filter_service.js';

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

export function handlePreview(el, active) {
    const url = el.getAttribute('data-preview-url');
    if (!url) return;
    const container = el.querySelector('.preview-container');
    if (active) container.innerHTML = `<video class="preview-video w-full h-full object-cover" muted loop playsinline autoplay><source src="${url}" type="video/mp4"></video>`;
    else container.innerHTML = '';
}

export function showInfo(e, index) {
    e.stopPropagation();
    const v = state.currentGridVideos[index];
    alert(`Tên: ${v.name}\nSize: ${v.size_fmt}\nView: ${v.views || 0}\nFolder: ${v.folder || 'Gốc'}`);
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
