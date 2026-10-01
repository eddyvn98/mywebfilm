import { state } from './state.js';
import { getThumbnailUrl, getPreviewUrl } from './api.js';
import { favoritesService } from './favorites_service.js';
import { escapeHtml, escapeAttr, escapeInlineJsSingleQuoted } from './security.js';

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export function renderGrid(videos, append = false, resetPage = true) {
    const grid = document.getElementById('video-grid');
    if (!grid) return;

    if (!append) {
        if (resetPage) state.currentPage = 1;
        grid.innerHTML = '';
        state.currentGridVideos = videos;
    }

    if (videos.length === 0 && !append) {
        grid.innerHTML = `
            <div class="col-span-full py-40 text-center text-slate-700 font-bold italic text-sm flex flex-col items-center gap-4">
                <span>KHÔNG CÓ PHIM</span>
                <button onclick="window.resetFilters()" class="px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600 hover:text-white transition text-xs font-black uppercase tracking-widest">
                    <i class="fa-solid fa-filter-circle-xmark mr-2"></i>Xóa bộ lọc
                </button>
            </div>`;
        return;
    }

    const start = append ? (state.currentPage - 1) * state.pageSize : 0;
    const end = state.currentPage * state.pageSize;
    const pagedVideos = videos.slice(start, end);

    if (pagedVideos.length === 0) return;

    // Grouping by Date
    const groups = {};
    pagedVideos.forEach((v, index) => {
        const date = new Date(v.date_added * 1000);
        const dateKey = date.toLocaleDateString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit' });
        if (!groups[dateKey]) groups[dateKey] = [];
        groups[dateKey].push({ v, globalIndex: start + index });
    });

    const html = Object.entries(groups).map(([date, items]) => {
        const groupHtml = items.map(({ v, globalIndex }) => {
            const isImage = v.type === 'image';
            const isSelected = state.selectedPaths?.includes(v.full_path);
            const previewAttr = isImage ? '' : `data-preview-url="${escapeAttr(getPreviewUrl(v.full_path))}"`;

            return `
            <div class="movie-card group cursor-pointer relative ${isSelected ? 'selected' : ''} ${v.is_offline ? 'opacity-60 saturate-0' : ''}" 
                 data-path="${escapeAttr(v.full_path)}"
                 onclick="handleCardClick(event, ${globalIndex})"
                 onmouseenter="handlePreview(this, true); handleMouseEnter(event, ${globalIndex})"
                 onmouseleave="handlePreview(this, false)"
                 ${previewAttr}>
                <div class="poster-container bg-slate-900 overflow-hidden rounded-2xl border border-white/5 shadow-2xl transition duration-500">
                    <div class="poster-content h-full w-full relative">
                        <img src="${escapeAttr(getThumbnailUrl(v.full_path, v.type))}" 
                             class="w-full h-full object-cover transition duration-500 ${v.is_offline ? '' : 'group-hover:scale-110'}" 
                             loading="lazy"
                             decoding="async"
                             onerror="this.style.display='none'">
                        
                        <div class="absolute top-2 right-2 flex flex-col gap-1 items-end z-10 pointer-events-none">
                            ${v.is_offline ? '<span class="badge bg-red-600 text-white px-2 py-0.5 rounded shadow-lg font-bold flex items-center gap-1"><i class="fa-solid fa-plug-circle-exclamation"></i> OFFLINE</span>' : ''}
                            ${isImage ? '<span class="badge bg-purple-600/90 text-white px-2 py-0.5 rounded shadow-lg">IMG</span>' : ''}
                            <span class="badge ${isImage ? 'bg-purple-900/80 text-purple-200 border-purple-500/30' : 'bg-blue-900/80 text-blue-200 border-blue-500/30'} 
                                 px-2 py-0.5 rounded border shadow-md">${escapeHtml(v.ext)}</span>
                            ${(v.categories || []).map(c => {
                let color = 'bg-blue-600/80';
                let label = c;
                if (c.startsWith('Studio:')) { color = 'bg-indigo-600/80'; label = c.replace('Studio: ', ''); }
                else if (c.startsWith('Diễn viên:')) { color = 'bg-teal-600/80'; label = c.replace('Diễn viên: ', ''); }
                return `<span class="badge ${color} text-white px-1.5 py-0.5 rounded text-[7px] uppercase tracking-tighter pointer-events-auto hover:brightness-125 transition" 
                                               onclick="handleBadgeClick(event, '${escapeInlineJsSingleQuoted(c)}', '${escapeInlineJsSingleQuoted(label.toUpperCase())}')">
                                            ${escapeHtml(label)}
                                        </span>`;
            }).join('')}
                        </div>
    
                        ${v.duration > 0 ? `
                        <div class="absolute bottom-2 right-2 bg-black/75 text-white text-[10px] px-1.5 py-0.5 rounded-md font-bold z-10 pointer-events-none border border-white/10">
                            ${formatDuration(v.duration)}
                        </div>` : ''}

                        <div class="card-actions absolute top-2 left-2 flex gap-1 z-50 opacity-0 group-hover:opacity-100 transition duration-300">
                            <button onclick="openRenameModal(event, ${globalIndex})" 
                                    class="w-7 h-7 rounded-lg bg-blue-600/90 text-white flex items-center justify-center hover:bg-blue-500 border border-white/10 shadow-lg ${v.is_offline ? 'hidden' : ''}">
                                <i class="fa-solid fa-pen text-[9px]"></i>
                            </button>
                            ${v.ext && v.ext.toLowerCase() === '.ts' ? `
                                <button onclick="processConvert(event, ${globalIndex})" 
                                        class="w-7 h-7 rounded-lg bg-indigo-600/90 text-white flex items-center justify-center hover:bg-indigo-500 border border-white/10 shadow-lg"
                                        title="Convert to MP4">
                                    <i class="fa-solid fa-file-video text-[9px]"></i>
                                </button>` : ''}
                            <button onclick="deleteItem(event, ${globalIndex})" 
                                    class="w-7 h-7 rounded-lg bg-red-900/80 text-white flex items-center justify-center hover:bg-red-600 border border-white/10 shadow-lg ${v.is_offline ? 'hidden' : ''}">
                                <i class="fa-solid fa-trash-can text-[9px]"></i>
                            </button>
                        </div>

                        <!-- Favorite Heart -->
                        <button onclick="handleFavoriteToggle(event, ${globalIndex})" 
                                class="absolute bottom-2 left-2 z-[60] w-8 h-8 rounded-full bg-black/65 flex items-center justify-center transition hover:scale-110 active:scale-90 group/heart">
                            <i class="fa-${favoritesService.isFavorite(v.full_path) ? 'solid' : 'regular'} fa-heart ${favoritesService.isFavorite(v.full_path) ? 'text-red-500' : 'text-white/70 group-hover/heart:text-red-400'} transition"></i>
                        </button>
                    </div>
                </div>
                <div class="px-1 py-2">
                    <p class="movie-title mb-1.5 line-clamp-2" title="${escapeAttr(v.name)}">${escapeHtml(v.name)}</p>
                    <div class="flex items-center gap-1.5 opacity-40 text-[10px] font-bold tracking-tight">
                        <span class="font-mono uppercase">${escapeHtml(v.size_fmt)}</span>
                        <span class="opacity-50 text-[6px]">•</span>
                        <span class="uppercase">${v.views || 0} VIEW</span>
                    </div>
                </div>
            </div>`;
        }).join('');

        return `
            <div class="col-span-full mt-8 mb-4 flex items-center gap-4 group/header" id="date-${date.replace(/\//g, '-')}">
                <div class="h-px bg-white/10 flex-1"></div>
                <div class="bg-blue-600/20 text-blue-400 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase border border-blue-500/20 shadow-lg">${date}</div>
                <div class="h-px bg-white/10 flex-1"></div>
            </div>
            ${groupHtml}
        `;
    }).join('');

    if (append) {
        grid.insertAdjacentHTML('beforeend', html);
    } else {
        grid.innerHTML = html;
    }

    if (!append) {
        renderTimeline(videos);
    }
    setupInfiniteScroll();
}

export function renderTimeline(allVisibleVideos) {
    const timeline = document.getElementById('grid-timeline');
    if (!timeline) return;

    // Extract unique months or weeks for timeline
    const dates = allVisibleVideos.map(v => {
        const d = new Date(v.date_added * 1000);
        return {
            key: d.toLocaleDateString('vi-VN', { month: '2-digit', year: 'numeric' }),
            fullDate: d.toLocaleDateString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit' })
        };
    });

    const uniqueMonths = [...new Map(dates.map(item => [item.key, item])).values()];

    timeline.innerHTML = uniqueMonths.map(m => `
        <button onclick="scrollToDate('${m.fullDate}')" 
                class="group flex flex-col items-center gap-1 transition-transform hover:scale-110 active:scale-95">
            <span class="text-[8px] font-black text-slate-500 group-hover:text-blue-400 transition">${escapeHtml(m.key.split('/')[1])}</span>
            <div class="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-blue-500 shadow-lg shadow-blue-500/20 transition"></div>
            <span class="text-[9px] font-black text-slate-400 group-hover:text-white transition">${escapeHtml(m.key.split('/')[0])}</span>
        </button>
    `).join('');

    timeline.classList.toggle('hidden', uniqueMonths.length < 2);
}

window.scrollToDate = (date) => {
    const id = `date-${date.replace(/\//g, '-')}`;
    const el = document.getElementById(id);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

let scrollObserver = null;
function setupInfiniteScroll() {
    const grid = document.getElementById('video-grid');
    if (!grid) return;

    // Remove old sentinel
    document.getElementById('infinite-scroll-sentinel')?.remove();

    // Add new sentinel
    const sentinel = document.createElement('div');
    sentinel.id = 'infinite-scroll-sentinel';
    sentinel.className = 'col-span-full h-10 flex items-center justify-center';

    if (state.currentPage * state.pageSize < state.currentGridVideos.length) {
        sentinel.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin text-blue-500"></i>';
        grid.appendChild(sentinel);

        if (scrollObserver) scrollObserver.disconnect();
        scrollObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                state.currentPage++;
                renderGrid(state.currentGridVideos, true);
            }
        }, { threshold: 0.1 });

        scrollObserver.observe(sentinel);
    }
}

export function renderFolders() {
    console.log("renderFolders() called. allVideos count:", state.allVideos ? state.allVideos.length : 'NULL');
    const folders = [...new Set(state.allVideos.map(v => v.folder).filter(Boolean))].sort();
    console.log("Folders identified:", folders);

    const list = document.getElementById('folder-list');
    if (!list) {
        console.error("CRITICAL: #folder-list element NOT FOUND in document!");
        return;
    }

    list.innerHTML = `
        <button onclick="filterByFolder('all'); closeSidebarOnMobile()" class="folder-chip ${state.currentFolder === 'all' ? 'active' : ''}">TẤT CẢ</button>
        ${folders.map(f => `
            <button onclick="filterByFolder('${escapeInlineJsSingleQuoted(f)}'); closeSidebarOnMobile()" class="folder-chip ${state.currentFolder === f ? 'active' : ''}">${escapeHtml((f || 'GỐC').toUpperCase())}</button>
        `).join('')}
    `;
}

export function restoreScroll() {
    if (state.scrollPos) {
        setTimeout(() => {
            document.getElementById('video-grid')?.scrollTo({ top: state.scrollPos, behavior: 'auto' });
        }, 100);
    }
}
