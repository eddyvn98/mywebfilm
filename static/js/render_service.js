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
            <div class="col-span-full py-40 text-center text-slate-600 font-bold text-sm flex flex-col items-center gap-4">
                <div class="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
                    <i class="fa-solid fa-film text-2xl text-slate-500"></i>
                </div>
                <div>
                    <p class="text-slate-300">Không có phim phù hợp</p>
                    <p class="text-slate-600 text-xs mt-1 font-medium">Thử đổi bộ lọc hoặc thư mục đang xem.</p>
                </div>
                <button onclick="window.resetFilters()" class="px-4 py-2 bg-blue-600/15 text-blue-400 rounded-lg hover:bg-blue-600 hover:text-white transition text-xs font-black uppercase tracking-widest">
                    <i class="fa-solid fa-filter-circle-xmark mr-2"></i>Xóa bộ lọc
                </button>
            </div>`;
        return;
    }

    const startIndex = append ? (state.currentPage - 1) * state.pageSize : 0;
    const endIndex = state.currentPage * state.pageSize;
    const pagedVideos = videos.slice(startIndex, endIndex);
    if (!pagedVideos.length) return;

    const cards = pagedVideos.map((v, index) => {
        const globalIndex = startIndex + index;
        const isImage = v.type === 'image';
        const isSelected = state.selectedPaths?.includes(v.full_path);
        const previewAttr = isImage ? '' : `data-preview-url="${escapeAttr(getPreviewUrl(v.full_path))}"`;
        const categories = v.categories || [];
        const actress = categories.find(c => c.startsWith('Diễn viên:'))?.replace('Diễn viên:', '').trim() || '';
        const studio = categories.find(c => c.startsWith('Studio:'))?.replace('Studio:', '').trim() || '';
        const contentMeta = [actress, studio].filter(Boolean).join(' · ') || (v.folder || 'Thư viện cá nhân');
        const folderLabel = v.folder || 'Gốc';
        const extLabel = (v.ext || '').replace('.', '').toUpperCase();

        return `
        <article class="movie-card group cursor-pointer relative ${isSelected ? 'selected' : ''} ${v.is_offline ? 'opacity-60 saturate-0' : ''}"
             data-path="${escapeAttr(v.full_path)}"
             onclick="handleCardClick(event, ${globalIndex})"
             onmouseenter="handlePreview(this, true); handleMouseEnter(event, ${globalIndex})"
             onmouseleave="handlePreview(this, false)"
             ${previewAttr}>
            <div class="poster-container cinema-poster-card">
                <div class="poster-content h-full w-full relative">
                    <img src="${escapeAttr(getThumbnailUrl(v.full_path, v.type))}"
                         class="w-full h-full object-cover transition duration-500 ${v.is_offline ? '' : 'group-hover:scale-[1.04]'}"
                         loading="lazy" decoding="async"
                         onerror="this.style.display='none'">

                    <div class="movie-card-overlay"></div>

                    <div class="absolute top-2 right-2 flex flex-col gap-1 items-end z-20 pointer-events-none">
                        ${v.is_offline ? '<span class="cinema-status-badge bg-red-600/90 text-white"><i class="fa-solid fa-plug-circle-exclamation"></i> Offline</span>' : ''}
                        ${isImage ? '<span class="cinema-status-badge bg-purple-600/90 text-white">Ảnh</span>' : ''}
                    </div>

                    <div class="card-actions absolute top-2 left-2 flex gap-1.5 z-50 opacity-0 group-hover:opacity-100 transition duration-200">
                        <button onclick="showInfo(event, ${globalIndex})" class="cinema-action-btn" title="Thông tin & vị trí file">
                            <i class="fa-solid fa-circle-info text-[10px]"></i>
                        </button>
                        <button onclick="openRenameModal(event, ${globalIndex})" class="cinema-action-btn ${v.is_offline ? 'hidden' : ''}" title="Đổi tên">
                            <i class="fa-solid fa-pen text-[9px]"></i>
                        </button>
                        ${v.ext && v.ext.toLowerCase() === '.ts' ? `
                            <button onclick="processConvert(event, ${globalIndex})" class="cinema-action-btn" title="Convert to MP4">
                                <i class="fa-solid fa-file-video text-[9px]"></i>
                            </button>` : ''}
                        <button onclick="deleteItem(event, ${globalIndex})" class="cinema-action-btn cinema-action-danger ${v.is_offline ? 'hidden' : ''}" title="Xóa">
                            <i class="fa-solid fa-trash-can text-[9px]"></i>
                        </button>
                    </div>

                    <button onclick="handleFavoriteToggle(event, ${globalIndex})"
                            class="absolute bottom-2 left-2 z-[60] w-8 h-8 rounded-full bg-black/65 backdrop-blur-sm flex items-center justify-center transition hover:scale-110 active:scale-90 group/heart border border-white/10"
                            title="Yêu thích">
                        <i class="fa-${favoritesService.isFavorite(v.full_path) ? 'solid' : 'regular'} fa-heart ${favoritesService.isFavorite(v.full_path) ? 'text-red-500' : 'text-white/80 group-hover/heart:text-red-400'} transition"></i>
                    </button>

                    ${v.duration > 0 ? `
                    <div class="absolute bottom-2 right-2 bg-black/75 backdrop-blur-sm text-white text-[10px] px-1.5 py-0.5 rounded-md font-bold z-20 pointer-events-none border border-white/10">
                        ${formatDuration(v.duration)}
                    </div>` : ''}
                </div>
            </div>

            <div class="movie-card-body">
                <div class="flex items-start gap-2">
                    <div class="min-w-0 flex-1">
                        <p class="movie-title" title="${escapeAttr(v.name)}">${escapeHtml(v.name)}</p>
                        <p class="movie-card-meta" title="${escapeAttr(contentMeta)}">${escapeHtml(contentMeta)}</p>
                    </div>
                    ${extLabel ? `<span class="movie-ext-chip">${escapeHtml(extLabel)}</span>` : ''}
                </div>
                <button class="movie-folder-line" onclick="showInfo(event, ${globalIndex})" title="Xem vị trí file">
                    <i class="fa-regular fa-folder-open"></i>
                    <span>${escapeHtml(folderLabel)}</span>
                </button>
            </div>
        </article>`;
    }).join('');

    const heading = append ? '' : `
        <div class="cinema-grid-heading col-span-full">
            <div>
                <p class="cinema-grid-kicker">THƯ VIỆN CÁ NHÂN</p>
                <h2>Phim của bạn</h2>
            </div>
            <div class="cinema-grid-count">${videos.length.toLocaleString('vi-VN')} mục</div>
        </div>`;

    if (append) grid.insertAdjacentHTML('beforeend', cards);
    else {
        grid.innerHTML = heading + cards;
        const timeline = document.getElementById('grid-timeline');
        if (timeline) {
            timeline.innerHTML = '';
            timeline.classList.add('hidden');
        }
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
