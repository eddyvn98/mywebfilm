import { state, saveState } from './state.js';
import { renderGrid } from './render_service.js';
import { favoritesService } from './favorites_service.js';
import { historyService } from './history_service.js';
import { escapeHtml, escapeInlineJsSingleQuoted } from './security.js';
// closeDiscovery is used from window.closeDiscovery to avoid circular imports
let categorySource = null;

function closeDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
}

export function applyFilters(preserveScroll = false) {
    const grid = document.getElementById('video-grid');
    const currentScroll = preserveScroll ? (grid?.scrollTop || 0) : 0;
    const search = (document.getElementById('search')?.value || '').toLowerCase();
    const type = state.filterType || 'all';
    const sort = state.sortOrder || 'added_newest';

    let filtered = state.allVideos.filter(v => {
        let matchesSearch = true;
        if (search) {
            const meta = v.jav_metadata || {};
            const matchesName = v.name.toLowerCase().includes(search);
            const matchesCats = (v.categories || []).some(c => c.toLowerCase().includes(search));
            const matchesMetaTitle = (meta.title || '').toLowerCase().includes(search);
            const matchesMetaCode = (meta.code || '').toLowerCase().includes(search);
            matchesSearch = matchesName || matchesCats || matchesMetaTitle || matchesMetaCode;
        }

        // Favorites / History override
        if (state.currentFolder === 'favorites') {
            return matchesSearch && favoritesService.isFavorite(v.full_path);
        }
        if (state.currentFolder === 'history') {
            const histPaths = historyService.getHistoryPaths() || [];
            return matchesSearch && histPaths.includes(v.full_path);
        }

        const matchesFolder = state.currentFolder === 'all' || v.folder === state.currentFolder;
        const matchesType = type === 'all' || v.type === type;

        const ext = v.ext.toLowerCase().replace('.', '');
        const matchesExt = state.filterExt === 'all' || ext === state.filterExt;

        const cat = state.currentCategory || 'all';
        const matchesCategory = cat === 'all' || (v.categories && v.categories.includes(cat));

        return matchesSearch && matchesFolder && matchesType && matchesExt && matchesCategory;
    });

    if (sort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === 'name_desc') filtered.sort((a, b) => b.name.localeCompare(a.name));
    else if (sort === 'views_desc') filtered.sort((a, b) => (b.views || 0) - (a.views || 0));
    else if (sort === 'newest') filtered.sort((a, b) => b.mtime - a.mtime);
    else if (sort === 'duration_desc') filtered.sort((a, b) => (b.duration || 0) - (a.duration || 0));
    else if (sort === 'duration_asc') filtered.sort((a, b) => (a.duration || 0) - (b.duration || 0));
    else if (sort === 'size_desc') filtered.sort((a, b) => (b.size || 0) - (a.size || 0));
    else if (sort === 'size_asc') filtered.sort((a, b) => (a.size || 0) - (b.size || 0));
    else filtered.sort((a, b) => b.date_added - a.date_added);

    // If preserveScroll is true, we don't want to reset to page 1
    // Special sorting for history: preserve history order
    if (state.currentFolder === 'history') {
        const histPaths = historyService.getHistoryPaths() || [];
        filtered.sort((a, b) => histPaths.indexOf(a.full_path) - histPaths.indexOf(b.full_path));
    }

    renderGrid(filtered, false, !preserveScroll);
    saveState();

    const statsEl = document.getElementById('stats');
    if (statsEl) statsEl.innerText = `${filtered.length} FILE`;

    renderDynamicCategories();

    if (preserveScroll) {
        // Small delay to ensure render is complete
        setTimeout(() => grid?.scrollTo({ top: currentScroll, behavior: 'auto' }), 0);
    }
}

// Update to target the new Global Sheet list
export function renderDynamicCategories() {
    const list = document.getElementById('dynamic-studios-list-sheet');
    if (!list) return;
    if (categorySource === state.allVideos && list.childElementCount > 0) return;

    list.innerHTML = '';
    const sections = {
        'Studio': new Set(),
        'Diễn viên': new Set(),
        'Chủ đề': new Set()
    };
    const categoryCounts = new Map();

    const predefined = [
        'Học sinh / Teen', 'Show hàng / Live', 'Thủ dâm / Solo',
        'Gái múp / Vú to', 'Gạ gẫm / Call sex', 'Người quen / MILF'
    ];

    // Build category sets and counts in one pass. The previous implementation
    // rescanned the full library once per category, which becomes expensive
    // with thousands of movies and large actor/studio lists.
    state.allVideos.forEach(v => {
        (v.categories || []).forEach(c => {
            categoryCounts.set(c, (categoryCounts.get(c) || 0) + 1);
            if (c.startsWith('Studio:')) sections['Studio'].add(c.replace('Studio: ', ''));
            else if (c.startsWith('Diễn viên:')) sections['Diễn viên'].add(c.replace('Diễn viên: ', ''));
            else if (predefined.includes(c)) sections['Chủ đề'].add(c);
        });
    });

    let html = '';
    for (const [title, items] of Object.entries(sections)) {
        const sorted = Array.from(items).sort();
        const sectionHtml = sorted.map(s => {
            const val = title === 'Chủ đề' ? s : `${title}: ${s}`;
            const count = categoryCounts.get(val) || 0;
            if (count === 0) return '';
            return `
                <div class="dropdown-item flex justify-between items-center group/cat" onclick="selectCategory('${escapeInlineJsSingleQuoted(val)}', '${escapeInlineJsSingleQuoted(s.toUpperCase())}'); event.stopPropagation(); event.preventDefault()">
                    <span class="truncate pr-2">${escapeHtml(s)}</span>
                    <span class="text-[8px] opacity-40 group-hover/cat:opacity-100 transition shrink-0">${count}</span>
                </div>
            `;
        }).join('');

        if (sectionHtml.trim()) {
            html += `<div class="px-3 py-1 text-[8px] font-bold text-slate-500 uppercase tracking-widest mt-2 border-b border-white/5 pb-1 mb-1">${escapeHtml(title)}</div>`;
            html += sectionHtml;
        }
    }
    list.innerHTML = html || '<div class="px-3 py-4 text-center text-slate-700 italic text-[10px]">Trống</div>';
    categorySource = state.allVideos;
}

export function selectType(val, label) {
    state.filterType = val;
    state.filterExt = 'all';
    document.getElementById('type-label').innerText = label;
    // Micro-delay to prevent ghost clicks on elements behind the menu
    setTimeout(() => {
        closeDropdowns();
        window.closeAllActionSheets?.();
        applyFilters();
    }, 50);
}

export function selectExt(val, label) {
    state.filterExt = val;
    state.filterType = 'all';
    document.getElementById('type-label').innerText = label;
    setTimeout(() => {
        closeDropdowns();
        window.closeAllActionSheets?.();
        applyFilters();
    }, 50);
}

export function selectCategory(val, label) {
    state.currentCategory = val;
    const labelEl = document.getElementById('category-label');
    if (labelEl) labelEl.innerText = label;
    setTimeout(() => {
        closeDropdowns();
        window.closeAllActionSheets?.();
        applyFilters();
        if (window.closeDiscovery) window.closeDiscovery();
    }, 50);
}

// Attach to window for global access from empty state button
window.resetFilters = function () {
    state.currentFolder = 'all';
    state.filterType = 'all';
    state.filterExt = 'all';
    state.currentCategory = 'all';
    const searchInput = document.getElementById('search');
    if (searchInput) searchInput.value = '';

    // Reset select inputs (custom dropdowns handled by state reflow in main logic, but UI needs sync)
    // For now, applyFilters() triggers saving state. A full reload might be better but this works.
    applyFilters();

    // Sync UI labels if elements exist
    const typeLabel = document.getElementById('type-label');
    if (typeLabel) typeLabel.innerText = 'TẤT CẢ';
    const catLabel = document.getElementById('category-label');
    if (catLabel) catLabel.innerText = 'THỂ LOẠI';
};

export function selectSort(val, label) {
    state.sortOrder = val;
    const labelEl = document.getElementById('sort-label');
    if (labelEl) labelEl.innerText = label;
    setTimeout(() => {
        closeDropdowns();
        window.closeAllActionSheets?.();
        applyFilters();
    }, 50);
}

export function filterByFavorites() {
    state.currentFolder = 'favorites';
    applyFilters();
    // Update active UI
    const homeBtn = document.getElementById('btn-show-all');
    const favBtn = document.getElementById('btn-show-favorites');
    if (homeBtn) homeBtn.classList.replace('bg-blue-600/10', 'bg-slate-800/0');
    if (favBtn) favBtn.classList.replace('bg-red-600/0', 'bg-red-600/10');
}

export async function filterByHistory() {
    state.currentFolder = 'history';
    // Ensure history is loaded in service
    await historyService.loadHistoryData();
    applyFilters();

    // Update UI active state
    document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('bg-blue-600/10', 'bg-red-600/10')); // hypothetical
    // For now simple reset like filterByFavorites
    const homeBtn = document.getElementById('btn-show-all');
    const histBtn = document.getElementById('btn-show-history');
    if (homeBtn) {
        homeBtn.classList.remove('bg-blue-600/10');
        homeBtn.classList.add('bg-slate-800/0');
    }
    if (histBtn) {
        histBtn.classList.remove('bg-blue-600/0');
        histBtn.classList.add('bg-blue-600/10');
    }
}
