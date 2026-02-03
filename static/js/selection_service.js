// static/js/selection_service.js
import { state } from './state.js';
import { deleteFile, apiMkdir, apiMove } from './api.js';
import { renderGrid } from './render_service.js';
import { applyFilters } from './filter_service.js';
import { processHighlight, processConvert } from './queue_service.js';

export function toggleManageMode() {
    state.manageMode = !state.manageMode;
    const btn = document.getElementById('btn-manage-mode');
    const selectAllBtn = document.getElementById('btn-select-all');

    if (btn) btn.classList.toggle('manage-btn-active', state.manageMode);
    if (selectAllBtn) {
        if (state.manageMode) selectAllBtn.classList.remove('hidden');
        else selectAllBtn.classList.add('hidden');
    }

    if (!state.manageMode) cancelSelection();

    // Use resetPage = false to stay on current scroll position
    renderGrid(state.currentGridVideos, false, false);
}

let isDragSelecting = false;
window.addEventListener('mousedown', () => { if (state.manageMode) isDragSelecting = true; });
window.addEventListener('mouseup', () => { isDragSelecting = false; });

export function handleMouseEnter(e, index) {
    if (state.manageMode && isDragSelecting) {
        const path = state.currentGridVideos[index].full_path;
        if (!state.selectedPaths.includes(path)) {
            toggleSelection(index);
        }
    }
}

export function selectAll() {
    if (!state.manageMode) return;
    state.selectedPaths = state.currentGridVideos.map(v => v.full_path);
    document.querySelectorAll('.movie-card').forEach(card => card.classList.add('selected'));
    updateSelectionUI();
}

export function handleCardClick(e, index) {
    const v = state.currentGridVideos[index];
    if (state.manageMode) toggleSelection(index);
    else {
        if (v.is_offline) {
            alert("Ổ cứng chứa phim này đang tháo. Anh vui lòng cắm lại ổ cứng để xem nhé!");
            return;
        }
        window.playVideoFromIndex(index);
    }
}

export function toggleSelection(index) {
    if (!state.selectedPaths) state.selectedPaths = [];
    const path = state.currentGridVideos[index].full_path;
    const idx = state.selectedPaths.indexOf(path);
    const isAdding = idx === -1;

    if (isAdding) state.selectedPaths.push(path);
    else state.selectedPaths.splice(idx, 1);

    // Update UI directly without re-rendering the whole grid
    const cards = document.querySelectorAll(`.movie-card[data-path="${CSS.escape(path)}"]`);
    cards.forEach(card => {
        if (isAdding) card.classList.add('selected');
        else card.classList.remove('selected');
    });

    updateSelectionUI();
}

export function updateSelectionUI() {
    const toolbar = document.getElementById('selection-toolbar');
    const countEl = document.getElementById('selected-count');
    const count = (state.selectedPaths || []).length;

    if (count > 0) {
        toolbar.classList.add('show');
        countEl.innerText = count;
        let controls = `<button onclick="processHighlight(event)" class="h-9 px-4 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-[10px] font-black uppercase transition flex items-center gap-2">
            <i class="fa-solid fa-scissors"></i> Cắt Highlight ${count > 1 ? `(${count})` : ''}
        </button>
        <button onclick="processConvert(event)" class="h-9 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-black uppercase transition flex items-center gap-2">
            <i class="fa-solid fa-file-video"></i> Convert MP4
        </button>
        <button onclick="bulkMove()" class="h-9 px-4 rounded-xl bg-white/20 hover:bg-white/30 text-white text-[10px] font-black uppercase transition">Di chuyển</button>
        <button onclick="bulkDelete()" class="h-9 px-4 rounded-xl bg-red-500 hover:bg-red-400 text-white text-[10px] font-black uppercase transition">Xóa hết</button>`;
        const buttonContainer = toolbar.children[2];
        if (buttonContainer) buttonContainer.innerHTML = controls;
    } else {
        toolbar.classList.remove('show');
    }
}

export function cancelSelection() {
    state.selectedPaths = [];
    document.querySelectorAll('.movie-card.selected').forEach(el => el.classList.remove('selected'));
    updateSelectionUI();
}

export async function bulkDelete() {
    if (!state.selectedPaths?.length) return;
    if (confirm('Xóa ' + state.selectedPaths.length + ' file?')) {
        for (const path of state.selectedPaths) await deleteFile(path);
        state.allVideos = state.allVideos.filter(v => !state.selectedPaths.includes(v.full_path));
        cancelSelection();
        applyFilters(true);
    }
}

export async function bulkMove() {
    const folders = [...new Set(state.allVideos.map(v => v.folder).filter(Boolean))].sort();
    const target = prompt('Di chuyển vào?\n' + folders.join(', '));
    if (!target) return;

    try {
        const configRes = await fetch('/api/config');
        const config = await configRes.json();
        const baseDir = config.video_dirs[0];
        const targetPath = baseDir + '\\' + target;

        await apiMkdir(baseDir, target);
        const res = await apiMove(state.selectedPaths, targetPath);

        if (res.status === 'ok') {
            for (const item of res.results) {
                if (item.status === 'ok') {
                    const v = state.allVideos.find(x => x.full_path === item.path);
                    if (v) { v.full_path = item.new_path; v.folder = target; }
                }
            }
            cancelSelection();
            applyFilters(true);
        } else {
            alert('Lỗi: ' + (res.msg || 'Không rõ'));
        }
    } catch (err) {
        alert('Lỗi: ' + err.message);
    }
}
