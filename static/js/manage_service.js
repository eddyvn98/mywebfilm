// static/js/manage_service.js
import { state } from './state.js';
import { deleteFile, apiRename, apiMove, apiMkdir, apiProcessHighlight, apiAddQueue, apiGetQueueStatus, apiClearQueue, apiProcessConvert } from './api.js';
import { renderGrid } from './render_service.js';
import { applyFilters } from './filter_service.js';

export function toggleManageMode() {
    state.manageMode = !state.manageMode;
    const btn = document.getElementById('btn-manage-mode');
    if (btn) btn.classList.toggle('manage-btn-active', state.manageMode);
    if (!state.manageMode) cancelSelection();
    renderGrid(state.currentGridVideos);
}

export function handleCardClick(e, index) {
    if (state.manageMode) toggleSelection(index);
    else window.playVideoFromIndex(index);
}

export function toggleSelection(index) {
    if (!state.selectedPaths) state.selectedPaths = [];
    const path = state.currentGridVideos[index].full_path;
    const idx = state.selectedPaths.indexOf(path);
    if (idx > -1) state.selectedPaths.splice(idx, 1);
    else state.selectedPaths.push(path);
    updateSelectionUI();
    renderGrid(state.currentGridVideos);
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

export async function processHighlight(e, index) {
    console.log("processHighlight called", e, index);
    if (e && e.stopPropagation) e.stopPropagation();

    let paths = [];
    if (typeof index === 'number') {
        const v = state.currentGridVideos[index];
        if (v) paths = [v.full_path];
    } else if (state.selectedPaths && state.selectedPaths.length > 0) {
        paths = [...state.selectedPaths];
    }

    console.log("Paths to highlight:", paths);

    if (paths.length === 0) {
        console.warn("No paths selected for highlight");
        return;
    }

    // Bypass confirm for debugging
    // const msg = paths.length === 1 ? `Tạo highlight?` : `Tạo highlight cho ${paths.length} file?`;
    // console.log("Showing confirm dialog...");
    // if (!confirm(msg)) {
    //     console.log("User cancelled confirm");
    //     return;
    // }
    console.log("Auto-confirmed. Starting API call...");

    const btn = e?.target?.closest('button') || document.querySelector('button[onclick="processHighlight()"]');
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang thêm...'; btn.disabled = true; }

    try {
        console.log("Calling apiAddQueue with paths:", paths);
        const res = await apiAddQueue(paths);
        console.log("API Result:", res);

        if (res.status === 'ok') {
            console.log("Queue added successfully. Starting polling...");
            cancelSelection();
            startQueuePolling();
        }
        else alert("Lỗi server: " + (res.msg || "Không thể thêm vào hàng đợi"));
    } catch (err) {
        console.error("Catch Error:", err);
        alert("Lỗi kết nối:\n" + err.message);
    }
    finally { if (btn) { btn.innerHTML = '<i class="fa-solid fa-scissors"></i> Cắt Highlight'; btn.disabled = false; } }
}

export async function processConvert(e) {
    console.log("processConvert called"); // Debug log only
    e?.stopPropagation();
    let paths = [];
    if (state.selectedPaths && state.selectedPaths.length > 0) {
        paths = [...state.selectedPaths];
    }

    if (paths.length === 0) {
        alert("Chưa chọn file nào! (state.selectedPaths is empty)");
        return;
    }

    // Skip confirm for debug
    // if (!confirm(`Debug: Bạn có chắc muốn convert ${paths.length} file này không?`)) return;

    const btn = e?.target?.closest('button') || document.querySelector('button[onclick="processConvert()"]');
    const originalText = btn ? btn.innerHTML : '';
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi...'; btn.disabled = true; }

    try {
        alert(`Bắt đầu gửi ${paths.length} file lên server...`);
        const res = await apiProcessConvert(paths);
        console.log("Convert result:", res);

        if (res.status === 'ok') {
            cancelSelection();
            startQueuePolling();
            alert("Thành công! Đã thêm vào hàng đợi.");
        } else {
            alert("Lỗi từ Server: " + (res.msg || "Unknown error"));
        }
    } catch (err) {
        alert("Lỗi Exception: " + err.message);
    } finally {
        if (btn) { btn.innerHTML = originalText || '<i class="fa-solid fa-file-video"></i> Convert MP4'; btn.disabled = false; }
    }
}

let queuePollInterval = null;
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
        const oldQueued = JSON.stringify(state.queuedPaths);
        state.queuedPaths = status.items.filter(i => i.status === 'pending' || i.status === 'processing').map(i => i.path);
        if (oldQueued !== JSON.stringify(state.queuedPaths)) applyFilters();
        if (status.items.length === 0 || (status.active_count === 0 && completedCount + failedCount === 0)) {
            overlay.classList.add('translate-x-80'); setTimeout(() => overlay.remove(), 500);
            clearInterval(queuePollInterval); queuePollInterval = null; return;
        }
        const currentType = activeItem ? (activeItem.type === 'convert' ? 'Chuyển đổi' : 'Highlight') : 'Hàng đợi';
        overlay.innerHTML = `<div class="flex items-center justify-between mb-3">
            <h4 class="text-white font-black text-[10px] uppercase tracking-wider">${currentType}</h4>
            ${status.active_count === 0 ? `<button onclick="clearCompletedQueue()" class="text-blue-400 text-[9px] font-bold hover:underline">Xong</button>` : ''}
        </div>
        ${activeItem ? `<div class="bg-blue-600/20 rounded-xl p-3 mb-3 border border-blue-500/30">
            <div class="flex items-center gap-2 mb-1">
                <i class="fa-solid ${activeItem.type === 'convert' ? 'fa-video' : 'fa-scissors'} text-blue-400 text-[10px]"></i>
                <span class="text-white text-[10px] font-bold truncate">${activeItem.name}</span>
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
            window.refreshLibrary(); overlay.dataset.refreshed = "true";
        }
    } catch (e) { console.error("Queue poll error:", e); }
}

export async function clearCompletedQueue() { await apiClearQueue(); updateQueueUI(); }
export function cancelSelection() { state.selectedPaths = []; updateSelectionUI(); renderGrid(state.currentGridVideos); }

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
        closeRenameModal(); applyFilters();
    } else { alert(res.msg || 'Lỗi'); }
}

export async function bulkDelete() {
    if (!state.selectedPaths?.length) return;
    if (confirm('Xóa ' + state.selectedPaths.length + ' file?')) {
        for (const path of state.selectedPaths) await deleteFile(path);
        state.allVideos = state.allVideos.filter(v => !state.selectedPaths.includes(v.full_path));
        cancelSelection(); applyFilters();
    }
}

export async function bulkMove() {
    const folders = [...new Set(state.allVideos.map(v => v.folder).filter(Boolean))].sort();
    const target = prompt('Di chuyển vào?\n' + folders.join(', '));
    if (!target) return;
    const config = await (await fetch('/api/config')).json();
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
        cancelSelection(); applyFilters();
    } else alert('Lỗi: ' + (res.msg || 'Không rõ'));
}

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
        if (res.ok) { state.allVideos = state.allVideos.filter(item => item.full_path !== v.full_path); applyFilters(); }
    }
}

// AI Management Studio Functions
let mgmtListVisible = [];
let allTags = { genres: [], actors: [], studios: [] };

export async function openAiLab() {
    const overlay = document.getElementById('ai-lab-overlay');
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.remove('translate-y-full'), 10);
    loadUnverifiedList();
    loadAllTags();
}

export async function loadAllTags() {
    try {
        const res = await fetch('/api/tags');
        allTags = await res.json();
        renderMgmtSidebars();
        renderActorQuickSelect();
    } catch (err) {
        console.error("Failed to load tags:", err);
    }
}

export function closeAiLab() {
    const overlay = document.getElementById('ai-lab-overlay');
    overlay.classList.add('translate-y-full');
    setTimeout(() => overlay.classList.add('hidden'), 500);
}

export async function loadUnverifiedList() {
    const listEl = document.getElementById('mgmt-file-list');
    listEl.innerHTML = '<div class="text-center py-10"><i class="fa-solid fa-spinner fa-spin text-slate-700"></i></div>';

    try {
        const res = await fetch('/api/admin/unverified');
        state.mgmtList = await res.json();
        mgmtListVisible = [...state.mgmtList];
        renderMgmtList();
        updateMgmtCount();
    } catch (err) {
        listEl.innerHTML = `<div class="text-red-500 text-[8px] p-4">Lỗi: ${err.message}</div>`;
    }
}

function renderMgmtList() {
    const listEl = document.getElementById('mgmt-file-list');
    const searchVal = document.getElementById('mgmt-search')?.value.toLowerCase() || "";

    mgmtListVisible = state.mgmtList.filter(v => v.name.toLowerCase().includes(searchVal));

    if (mgmtListVisible.length === 0) {
        listEl.innerHTML = '<div class="text-center py-10 text-slate-600 text-[8px] uppercase font-black italic">Không có file nào</div>';
        return;
    }

    listEl.innerHTML = mgmtListVisible.map((v, i) => `
        <div onclick="selectFileForMgmt(${i})" 
            class="group p-3 rounded-xl cursor-pointer transition-all duration-300 border border-transparent hover:bg-white/5 hover:border-white/5 ${state.mgmtSelectedIndex === i ? 'bg-blue-600/20 border-blue-500/30' : ''}">
            <div class="flex items-center gap-3">
                <div class="w-8 h-10 bg-slate-800 rounded flex items-center justify-center group-hover:bg-slate-700 transition">
                    <i class="fa-solid fa-file-video text-slate-600 text-[10px]"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-white text-[10px] font-bold truncate">${v.name}</div>
                    <div class="text-slate-500 text-[8px] uppercase font-black tracking-tighter">${v.ext} • ${v.size_fmt}</div>
                </div>
            </div>
        </div>
    `).join('');
}

function updateMgmtCount() {
    const el = document.getElementById('mgmt-count');
    if (el) el.innerText = `${mgmtListVisible.length} File Chờ`;
}

// Search listener for mgmt
document.getElementById('mgmt-search')?.addEventListener('input', () => {
    renderMgmtList();
    updateMgmtCount();
});

export function selectFileForMgmt(index) {
    state.mgmtSelectedIndex = index;
    const file = mgmtListVisible[index];
    if (!file) return;

    renderMgmtList(); // Refresh active state

    document.getElementById('mgmt-editor-empty').classList.add('hidden');
    document.getElementById('mgmt-editor-content').classList.remove('hidden');

    // Fill form with current data
    document.getElementById('mgmt-title').value = file.name;
    document.getElementById('mgmt-code').value = file.jav_metadata?.code || "";
    document.getElementById('mgmt-studio').value = file.jav_metadata?.studio || "";
    document.getElementById('mgmt-actors').value = (file.jav_metadata?.actors || []).join(', ');
    document.getElementById('mgmt-genres').value = (file.jav_metadata?.genres || []).join(', ');

    renderMgmtSidebars();
}

// Predefined genres for quick select
const PREDEFINED_GENRES = [
    'Học sinh / Teen', 'Show hàng / Live', 'Thủ dâm / Solo',
    'Gái múp / Vú to', 'Gạ gẫm / Call sex', 'Người quen / MILF',
    'Outdoor / Ngoài trời', 'Uniform / Đồng phục', 'JAV / Nhật Bản',
    'Amateur / Nghiệp dư', 'Cosplay', 'Bondage / Trói buộc'
];

function renderMgmtSidebars() {
    // 1. Render Actors Gallery
    const actorsStr = document.getElementById('mgmt-actors').value;
    const actors = actorsStr.split(',').map(s => s.trim()).filter(Boolean);
    const galleryEl = document.getElementById('mgmt-actor-gallery');

    if (actors.length === 0) {
        galleryEl.innerHTML = '<div class="col-span-2 text-center py-10 text-slate-700 text-[8px] uppercase font-black italic">Trống</div>';
    } else {
        galleryEl.innerHTML = actors.map(name => {
            const safeName = name.replace(/ /g, '_');
            const imgPath = `/static/img/actors/${safeName}.jpg?t=${Date.now()}`;
            return `
                <div class="relative aspect-square rounded-xl overflow-hidden bg-slate-800 border border-white/5 group shadow-lg">
                    <img src="${imgPath}" class="w-full h-full object-cover" 
                        onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect width=%22100%22 height=%22100%22 fill=%22%231e293b%22/><text x=%2250%%22 y=%2250%%22 font-family=%22Arial%22 font-size=%2210%22 fill=%22%23475569%22 text-anchor=%22middle%22 dy=%22.3em%22 uppercase>${name.substring(0, 2)}</text></svg>'">
                    <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center p-2 text-center">
                        <span class="text-[8px] text-white font-black uppercase mb-2 truncate w-full">${name}</span>
                        <input type="file" id="upload-${safeName}" class="hidden" onchange="uploadActorImage('${name}', this)">
                        <button onclick="document.getElementById('upload-${safeName}').click()" 
                            class="bg-blue-600 p-1.5 rounded-lg text-white hover:bg-blue-500 transition active:scale-95 shadow-lg">
                            <i class="fa-solid fa-camera text-[10px]"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 2. Render Genre Chips (Dynamic)
    const chipsEl = document.getElementById('mgmt-genre-chips');
    const currentGenres = document.getElementById('mgmt-genres').value.toLowerCase().split(',').map(s => s.trim());

    // Merge predefined with server tags
    let mergedGenres = [...new Set([...(allTags.genres || []), ...PREDEFINED_GENRES])].sort();

    chipsEl.innerHTML = mergedGenres.map(g => {
        const isActive = currentGenres.includes(g.toLowerCase());
        return `
            <button onclick="toggleGenreTag('${g}')" 
                class="px-2.5 py-1.5 rounded-lg text-[8px] font-black uppercase tracking-widest transition-all duration-300 border ${isActive ? 'bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-600/20' : 'bg-white/5 text-slate-500 border-white/5 hover:bg-white/10 hover:text-slate-300'}">
                ${g}
            </button>
        `;
    }).join('');

    // 3. Render Studio Quick Select
    const currentStudio = document.getElementById('mgmt-studio').value.trim();
    const studioContainer = document.getElementById('mgmt-studio-list');
    if (studioContainer) {
        let studios = (allTags.studios || []).sort();
        studioContainer.innerHTML = studios.map(s => {
            const isActive = currentStudio.toLowerCase() === s.toLowerCase();
            return `<button onclick="setStudio('${s}')" class="px-2 py-1 rounded text-[8px] border transition ${isActive ? 'bg-indigo-600 text-white border-indigo-500' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'}">${s}</button>`;
        }).join('');
    }

    renderActorQuickSelect();
}

// Global helper for setting studio
window.setStudio = function (val) {
    document.getElementById('mgmt-studio').value = val;
    renderMgmtSidebars();
}


export function toggleGenreTag(genre) {
    const el = document.getElementById('mgmt-genres');
    let genres = el.value.split(',').map(s => s.trim()).filter(Boolean);
    const idx = genres.findIndex(g => g.toLowerCase() === genre.toLowerCase());

    if (idx > -1) {
        genres.splice(idx, 1);
    } else {
        genres.push(genre);
    }

    el.value = genres.join(', ');
    renderMgmtSidebars();
}

export async function uploadActorImage(name, input) {
    if (!input.files || !input.files[0]) return;

    const formData = new FormData();
    formData.append('image', input.files[0]);
    formData.append('name', name);

    try {
        const res = await fetch('/api/admin/upload_actor_image', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.status === 'ok') {
            renderMgmtSidebars(); // Re-render to show new image
        } else {
            alert("Lỗi upload: " + (data.msg || "Không rõ"));
        }
    } catch (err) {
        alert("Lỗi kết nối: " + err.message);
    }
}

function renderActorQuickSelect() {
    const container = document.getElementById('mgmt-all-actors-list');
    if (!container) return;

    const currentActors = document.getElementById('mgmt-actors').value.toLowerCase().split(',').map(s => s.trim());
    const allActors = (allTags.actors || []).sort();

    if (allActors.length === 0) {
        container.innerHTML = '<div class="text-slate-600 text-[8px] italic">Chưa có dữ liệu</div>';
        return;
    }

    container.innerHTML = allActors.map(actor => {
        const isActive = currentActors.includes(actor.toLowerCase());
        return `
            <button onclick="toggleActorTag('${actor}')" 
                class="px-2 py-1 rounded text-[8px] border transition text-left truncate w-full ${isActive ? 'bg-purple-600 text-white border-purple-500' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'}">
                ${actor}
            </button>
        `;
    }).join('');
}

export function toggleActorTag(actor) {
    const el = document.getElementById('mgmt-actors');
    let actors = el.value.split(',').map(s => s.trim()).filter(Boolean);
    const idx = actors.findIndex(a => a.toLowerCase() === actor.toLowerCase());

    if (idx > -1) {
        actors.splice(idx, 1);
    } else {
        actors.push(actor);
    }

    el.value = actors.join(', ');
    renderMgmtSidebars();
    renderActorQuickSelect();
}

// Sync sidebars when typing
document.getElementById('mgmt-actors')?.addEventListener('input', renderMgmtSidebars);
document.getElementById('mgmt-genres')?.addEventListener('input', renderMgmtSidebars);

export function parseJsonMetadata() {
    const input = document.getElementById('mgmt-json-input');
    if (!input || !input.value.trim()) {
        alert("Vui lòng nhập JSON vào ô trống!");
        return;
    }

    try {
        const data = JSON.parse(input.value);

        if (data.title) document.getElementById('mgmt-title').value = data.title;
        if (data.code) document.getElementById('mgmt-code').value = data.code;
        if (data.studio) document.getElementById('mgmt-studio').value = data.studio;

        if (data.actors) {
            const actors = Array.isArray(data.actors) ? data.actors : [data.actors];
            document.getElementById('mgmt-actors').value = actors.join(', ');
        }

        if (data.genres) {
            const genres = Array.isArray(data.genres) ? data.genres : [data.genres];
            document.getElementById('mgmt-genres').value = genres.join(', ');
        }

        // Trigger updates for sidebars
        renderMgmtSidebars();
        renderActorQuickSelect();

        // alert("Đã điền thông tin từ JSON!");

    } catch (e) {
        alert("Lỗi JSON không hợp lệ: " + e.message);
    }
}

export async function runAiAnalyzeMgmt() {
    const file = mgmtListVisible[state.mgmtSelectedIndex];
    if (!file) return;

    const btn = document.getElementById('btn-run-ai-mgmt');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> ĐANG PHÂN TÍCH...';

    try {
        const res = await fetch('/api/ai/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name + "." + file.ext.toLowerCase() })
        });
        const data = await res.json();
        const r = data.result;

        if (r) {
            if (r.title) document.getElementById('mgmt-title').value = r.title;
            if (r.code) document.getElementById('mgmt-code').value = r.code;
            if (r.studio) document.getElementById('mgmt-studio').value = r.studio;
            if (r.actors) document.getElementById('mgmt-actors').value = r.actors.join(', ');
            if (r.genres) document.getElementById('mgmt-genres').value = r.genres.join(', ');
        }
    } catch (err) {
        alert("Lỗi AI: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

export async function finalizeMetadata() {
    const file = mgmtListVisible[state.mgmtSelectedIndex];
    if (!file) return;

    const btn = document.getElementById('btn-finalize');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> ĐANG THỰC THI...';

    const metadata = {
        title: document.getElementById('mgmt-title').value.trim(),
        code: document.getElementById('mgmt-code').value.trim(),
        studio: document.getElementById('mgmt-studio').value.trim(),
        actors: document.getElementById('mgmt-actors').value.split(',').map(s => s.trim()).filter(Boolean),
        genres: document.getElementById('mgmt-genres').value.split(',').map(s => s.trim()).filter(Boolean)
    };

    const shouldRename = document.getElementById('mgmt-rename').checked;

    try {
        const res = await fetch('/api/ai/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: file.name + "." + file.ext.toLowerCase(),
                path: file.full_path,
                metadata: metadata,
                rename: shouldRename
            })
        });
        const data = await res.json();

        if (data.status === 'ok') {
            // Xóa file khỏi list unverified
            state.mgmtList.splice(state.mgmtList.findIndex(v => v.full_path === file.full_path), 1);
            state.mgmtSelectedIndex = null;

            // Cập nhật UI
            renderMgmtList();
            updateMgmtCount();
            document.getElementById('mgmt-editor-content').classList.add('hidden');
            document.getElementById('mgmt-editor-empty').classList.remove('hidden');

            // Refresh main library
            window.refreshLibrary();

            alert("Hoàn tất! Metadata đã được chèn và file đã được chuẩn hóa.");
        } else {
            alert("Lỗi: " + data.msg);
        }
    } catch (err) {
        alert("Lỗi: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Global exposure
window.openAiLab = openAiLab;
window.closeAiLab = closeAiLab;
window.loadUnverifiedList = loadUnverifiedList;
window.selectFileForMgmt = selectFileForMgmt;
window.runAiAnalyzeMgmt = runAiAnalyzeMgmt;
window.parseJsonMetadata = parseJsonMetadata;
window.finalizeMetadata = finalizeMetadata;
window.processConvert = processConvert;
window.processHighlight = processHighlight;
window.bulkMove = bulkMove;
window.bulkDelete = bulkDelete;
window.toggleSelection = toggleSelection;
window.cancelSelection = cancelSelection;
window.showInfo = showInfo;
window.deleteItem = deleteItem;
window.toggleActorTag = toggleActorTag;
