// static/js/filter_service.js
import { state, saveState } from './state.js';
import { renderGrid } from './render_service.js';
// closeDiscovery is used from window.closeDiscovery to avoid circular imports

function closeDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
}

export function applyFilters() {
    const search = (document.getElementById('search')?.value || '').toLowerCase();
    const type = state.filterType || 'all';
    const sort = state.sortOrder || 'added_newest';

    let filtered = state.allVideos.filter(v => {
        const matchesName = v.name.toLowerCase().includes(search);
        const matchesCats = (v.categories || []).some(c => c.toLowerCase().includes(search));
        const matchesSearch = matchesName || matchesCats;

        const matchesFolder = state.currentFolder === 'all' || v.folder === state.currentFolder;
        const matchesType = type === 'all' || v.type === type;

        const ext = v.ext.toLowerCase().replace('.', '');
        const matchesExt = state.filterExt === 'all' || ext === state.filterExt;

        const cat = state.currentCategory || 'all';
        const matchesCategory = cat === 'all' || (v.categories && v.categories.includes(cat));

        return matchesSearch && matchesFolder && matchesType && matchesExt && matchesCategory;
    });

    if (sort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === 'views_desc') filtered.sort((a, b) => (b.views || 0) - (a.views || 0));
    else if (sort === 'newest') filtered.sort((a, b) => b.mtime - a.mtime);
    else filtered.sort((a, b) => b.date_added - a.date_added);

    renderGrid(filtered);
    saveState();

    const statsEl = document.getElementById('stats');
    if (statsEl) statsEl.innerText = `${filtered.length} FILE`;

    renderDynamicCategories();
}

export function renderDynamicCategories() {
    const list = document.getElementById('dynamic-studios-list');
    if (!list) return;

    const sections = {
        'Studio': new Set(),
        'Diễn viên': new Set(),
        'Chủ đề': new Set()
    };

    const predefined = [
        'Học sinh / Teen', 'Show hàng / Live', 'Thủ dâm / Solo',
        'Gái múp / Vú to', 'Gạ gẫm / Call sex', 'Người quen / MILF'
    ];

    state.allVideos.forEach(v => {
        (v.categories || []).forEach(c => {
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
            const count = state.allVideos.filter(v => v.categories?.includes(val)).length;
            if (count === 0) return '';
            return `
                <div class="dropdown-item flex justify-between items-center group/cat" onclick="selectCategory('${val}', '${s.toUpperCase()}'); event.stopPropagation()">
                    <span class="truncate pr-2">${s}</span>
                    <span class="text-[8px] opacity-40 group-hover/cat:opacity-100 transition shrink-0">${count}</span>
                </div>
            `;
        }).join('');

        if (sectionHtml.trim()) {
            html += `<div class="px-3 py-1 text-[8px] font-bold text-slate-500 uppercase tracking-widest mt-2 border-b border-white/5 pb-1 mb-1">${title}</div>`;
            html += sectionHtml;
        }
    }
    list.innerHTML = html || '<div class="px-3 py-4 text-center text-slate-700 italic text-[10px]">Trống</div>';
}

export function selectType(val, label) {
    state.filterType = val;
    state.filterExt = 'all';
    document.getElementById('type-label').innerText = label;
    closeDropdowns();
    applyFilters();
}

export function selectExt(val, label) {
    state.filterExt = val;
    state.filterType = 'all';
    document.getElementById('type-label').innerText = label;
    closeDropdowns();
    applyFilters();
}

export function selectCategory(val, label) {
    state.currentCategory = val;
    const labelEl = document.getElementById('category-label');
    if (labelEl) labelEl.innerText = label;
    closeDropdowns();
    applyFilters();
    if (window.closeDiscovery) window.closeDiscovery();
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
    closeDropdowns();
    applyFilters();
}
