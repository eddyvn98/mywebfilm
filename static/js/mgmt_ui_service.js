// static/js/mgmt_ui_service.js
import { state } from './state.js';
import { allTags, loadAllTags, uploadActorImage } from './ai_mgmt_service.js';
import { escapeHtml, escapeAttr, escapeInlineJsSingleQuoted } from './security.js';

export let mgmtListVisible = [];

const PREDEFINED_GENRES = [
    'Học sinh / Teen', 'Show hàng / Live', 'Thủ dâm / Solo',
    'Gái múp / Vú to', 'Gạ gẫm / Call sex', 'Người quen / MILF',
    'Outdoor / Ngoài trời', 'Uniform / Đồng phục', 'JAV / Nhật Bản',
    'Amateur / Nghiệp dư', 'Cosplay', 'Bondage / Trói buộc'
];

export function openAiLab() {
    const overlay = document.getElementById('ai-lab-overlay');
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.remove('translate-y-full'), 10);
    loadUnverifiedList();
    loadAllTags();
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
        listEl.innerHTML = `<div class="text-red-500 text-[8px] p-4">Lỗi: ${escapeHtml(err.message)}</div>`;
    }
}

export function renderMgmtList() {
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
                    <div class="text-white text-[10px] font-bold truncate">${escapeHtml(v.name)}</div>
                    <div class="text-slate-500 text-[8px] uppercase font-black tracking-tighter">${escapeHtml(v.ext)} • ${escapeHtml(v.size_fmt)}</div>
                </div>
            </div>
        </div>
    `).join('');
}

export function updateMgmtCount() {
    const el = document.getElementById('mgmt-count');
    if (el) el.innerText = `${mgmtListVisible.length} File Chờ`;
}

export function selectFileForMgmt(index) {
    state.mgmtSelectedIndex = index;
    const file = mgmtListVisible[index];
    if (!file) return;

    renderMgmtList();
    document.getElementById('mgmt-editor-empty').classList.add('hidden');
    document.getElementById('mgmt-editor-content').classList.remove('hidden');

    document.getElementById('mgmt-title').value = file.name;
    document.getElementById('mgmt-code').value = file.jav_metadata?.code || "";
    document.getElementById('mgmt-studio').value = file.jav_metadata?.studio || "";
    document.getElementById('mgmt-actors').value = (file.jav_metadata?.actors || []).join(', ');
    document.getElementById('mgmt-genres').value = (file.jav_metadata?.genres || []).join(', ');

    renderMgmtSidebars();
}

export function renderMgmtSidebars() {
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
                    <img src="${escapeAttr(imgPath)}" class="w-full h-full object-cover" 
                        onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect width=%22100%22 height=%22100%22 fill=%22%231e293b%22/><text x=%2250%%22 y=%2250%%22 font-family=%22Arial%22 font-size=%2210%22 fill=%22%23475569%22 text-anchor=%22middle%22 dy=%22.3em%22 uppercase>${escapeHtml(name.substring(0, 2))}</text></svg>'">
                    <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center p-2 text-center">
                        <span class="text-[8px] text-white font-black uppercase mb-2 truncate w-full">${escapeHtml(name)}</span>
                        <input type="file" id="upload-${escapeAttr(safeName)}" class="hidden" onchange="uploadActorImage('${escapeInlineJsSingleQuoted(name)}', this)">
                        <button onclick="document.getElementById('upload-${escapeInlineJsSingleQuoted(safeName)}').click()" 
                            class="bg-blue-600 p-1.5 rounded-lg text-white hover:bg-blue-500 transition active:scale-95 shadow-lg">
                            <i class="fa-solid fa-camera text-[10px]"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    const chipsEl = document.getElementById('mgmt-genre-chips');
    const currentGenres = document.getElementById('mgmt-genres').value.toLowerCase().split(',').map(s => s.trim());
    let mergedGenres = [...new Set([...(allTags.genres || []), ...PREDEFINED_GENRES])].sort();

    chipsEl.innerHTML = mergedGenres.map(g => {
        const isActive = currentGenres.includes(g.toLowerCase());
        return `
            <button onclick="toggleGenreTag('${escapeInlineJsSingleQuoted(g)}')" 
                class="px-2.5 py-1.5 rounded-lg text-[8px] font-black uppercase tracking-widest transition-all duration-300 border ${isActive ? 'bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-600/20' : 'bg-white/5 text-slate-500 border-white/5 hover:bg-white/10 hover:text-slate-300'}">
                ${escapeHtml(g)}
            </button>
        `;
    }).join('');

    const currentStudio = document.getElementById('mgmt-studio').value.trim();
    const studioContainer = document.getElementById('mgmt-studio-list');
    if (studioContainer) {
        let studios = (allTags.studios || []).sort();
        studioContainer.innerHTML = studios.map(s => {
            const isActive = currentStudio.toLowerCase() === s.toLowerCase();
            return `<button onclick="setStudio('${escapeInlineJsSingleQuoted(s)}')" class="px-2 py-1 rounded text-[8px] border transition ${isActive ? 'bg-indigo-600 text-white border-indigo-500' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'}">${escapeHtml(s)}</button>`;
        }).join('');
    }
    renderActorQuickSelect();
}

export function toggleGenreTag(genre) {
    const el = document.getElementById('mgmt-genres');
    let genres = el.value.split(',').map(s => s.trim()).filter(Boolean);
    const idx = genres.findIndex(g => g.toLowerCase() === genre.toLowerCase());
    if (idx > -1) genres.splice(idx, 1);
    else genres.push(genre);
    el.value = genres.join(', ');
    renderMgmtSidebars();
}

export function renderActorQuickSelect() {
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
            <button onclick="toggleActorTag('${escapeInlineJsSingleQuoted(actor)}')" 
                class="px-2 py-1 rounded text-[8px] border transition text-left truncate w-full ${isActive ? 'bg-purple-600 text-white border-purple-500' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:bg-slate-700'}">
                ${escapeHtml(actor)}
            </button>
        `;
    }).join('');
}

export function toggleActorTag(actor) {
    const el = document.getElementById('mgmt-actors');
    let actors = el.value.split(',').map(s => s.trim()).filter(Boolean);
    const idx = actors.findIndex(a => a.toLowerCase() === actor.toLowerCase());
    if (idx > -1) actors.splice(idx, 1);
    else actors.push(actor);
    el.value = actors.join(', ');
    renderMgmtSidebars();
    renderActorQuickSelect();
}
