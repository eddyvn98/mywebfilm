// static/js/render_service.js
import { state } from './state.js';
import { getThumbnailUrl, getPreviewUrl } from './api.js';

export function renderGrid(videos) {
    const grid = document.getElementById('video-grid');
    if (!grid) return;

    state.currentGridVideos = videos;

    if (videos.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full py-40 text-center text-slate-700 font-bold italic text-sm flex flex-col items-center gap-4">
                <span>KHÔNG CÓ PHIM</span>
                <button onclick="window.resetFilters()" class="px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600 hover:text-white transition text-xs font-black uppercase tracking-widest">
                    <i class="fa-solid fa-filter-circle-xmark mr-2"></i>Xóa bộ lọc
                </button>
            </div>`;
        return;
    }

    grid.innerHTML = videos.map((v, index) => {
        const isImage = v.type === 'image';
        const isSelected = state.selectedPaths?.includes(v.full_path);
        const previewAttr = isImage ? '' : `data-preview-url="${getPreviewUrl(v.full_path)}"`;

        return `
        <div class="movie-card group cursor-pointer relative ${isSelected ? 'selected' : ''}" 
             data-path="${v.full_path}"
             onclick="handleCardClick(event, ${index})"
             onmouseenter="handlePreview(this, true)"
             onmouseleave="handlePreview(this, false)"
             ${previewAttr}>
            <div class="poster-container bg-slate-900 overflow-hidden rounded-2xl border border-white/5 shadow-2xl transition duration-500">
                <div class="poster-content h-full w-full relative">
                    <img src="${getThumbnailUrl(v.full_path, v.type)}" 
                         class="w-full h-full object-cover transition duration-500 group-hover:scale-110" 
                         loading="lazy"
                         onerror="this.style.display='none'">
                    
                    <div class="preview-container absolute inset-0 hidden md:block pointer-events-none opacity-100 transition-opacity"></div>
                    
                    <div class="absolute top-2 right-2 flex flex-col gap-1 items-end z-10 pointer-events-none">
                        ${isImage ? '<span class="badge bg-purple-600/90 text-white px-2 py-0.5 rounded shadow-lg backdrop-blur-sm">IMG</span>' : ''}
                        <span class="badge ${isImage ? 'bg-purple-900/60 text-purple-200 border-purple-500/30' : 'bg-blue-900/60 text-blue-200 border-blue-500/30'} 
                             px-2 py-0.5 rounded border backdrop-blur-sm shadow-md">${v.ext}</span>
                        ${state.queuedPaths?.includes(v.full_path) ? '<span class="badge bg-orange-600/90 text-white px-2 py-0.5 rounded shadow-lg backdrop-blur-sm flex items-center gap-1 animate-pulse"><i class="fa-solid fa-spinner fa-spin text-[8px]"></i> CHỜ</span>' : ''}
                        ${(v.categories || []).map(c => {
            let color = 'bg-blue-600/80';
            let label = c;
            if (c.startsWith('Studio:')) { color = 'bg-indigo-600/80'; label = c.replace('Studio: ', ''); }
            else if (c.startsWith('Diễn viên:')) { color = 'bg-teal-600/80'; label = c.replace('Diễn viên: ', ''); }
            return `<span class="badge ${color} text-white px-1.5 py-0.5 rounded text-[7px] uppercase tracking-tighter pointer-events-auto hover:brightness-125 transition" 
                                          onclick="handleBadgeClick(event, '${c}', '${label.toUpperCase()}')">
                                        ${label}
                                    </span>`;
        }).join('')}
                    </div>

                    <div class="absolute top-2 left-2 flex gap-1 z-50 ${state.manageMode ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition duration-300">
                        <button onclick="openRenameModal(event, ${index})" 
                                class="w-7 h-7 rounded-lg bg-blue-600/80 text-white flex items-center justify-center hover:bg-blue-500 backdrop-blur-md border border-white/10 shadow-lg">
                            <i class="fa-solid fa-pen text-[9px]"></i>
                        </button>
                        <button onclick="processHighlight(event, ${index})" 
                                class="w-7 h-7 rounded-lg bg-purple-600/80 text-white flex items-center justify-center hover:bg-purple-500 backdrop-blur-md border border-white/10 shadow-lg"
                                title="Cắt Highlight">
                            <i class="fa-solid fa-scissors text-[9px]"></i>
                        </button>
                        <button onclick="showInfo(event, ${index})" 
                                class="w-7 h-7 rounded-lg bg-slate-900/60 text-white flex items-center justify-center hover:bg-slate-700 backdrop-blur-md border border-white/10 shadow-lg">
                            <i class="fa-solid fa-circle-info text-[9px]"></i>
                        </button>
                        <button onclick="deleteItem(event, ${index})" 
                                class="w-7 h-7 rounded-lg bg-red-900/60 text-white flex items-center justify-center hover:bg-red-600 backdrop-blur-md border border-white/10 shadow-lg">
                            <i class="fa-solid fa-trash-can text-[9px]"></i>
                        </button>
                    </div>

                    <div class="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition duration-300 flex items-center justify-center z-40 ${state.manageMode ? 'pointer-events-none' : ''}">
                         <div class="bg-blue-600/90 text-white w-12 h-12 rounded-full flex items-center justify-center shadow-2xl active:scale-90 transition transform backdrop-blur-sm">
                            <i class="fa-solid fa-play text-lg ml-1"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="px-1 py-2">
                <p class="movie-title mb-1.5 line-clamp-2" title="${v.name}">${v.name}</p>
                <div class="flex items-center gap-1.5 opacity-40 text-[10px] font-bold tracking-tight">
                    <span class="font-mono uppercase">${v.size_fmt}</span>
                    <span class="opacity-50 text-[6px]">•</span>
                    <span class="uppercase">${v.views || 0} VIEW</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

export function renderFolders() {
    const folders = [...new Set(state.allVideos.map(v => v.folder).filter(Boolean))].sort();
    const list = document.getElementById('folder-list');
    if (!list) return;

    list.innerHTML = `
        <button onclick="filterByFolder('all')" class="folder-chip ${state.currentFolder === 'all' ? 'active' : ''}">TẤT CẢ</button>
        ${folders.map(f => `
            <button onclick="filterByFolder('${f}')" class="folder-chip ${state.currentFolder === f ? 'active' : ''}">${(f || 'GỐC').toUpperCase()}</button>
        `).join('')}
    `;
}

export function restoreScroll() {
    if (state.scrollPos) {
        setTimeout(() => {
            window.scrollTo({ top: state.scrollPos, behavior: 'auto' });
        }, 100);
    }
}
