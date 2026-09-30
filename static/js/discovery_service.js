// static/js/discovery_service.js
import { state } from './state.js';
import { escapeHtml, escapeAttr, escapeInlineJsSingleQuoted } from './security.js';
// selectCategory is used from window.selectCategory to avoid circular imports

export function openDiscovery() {
    const overlay = document.getElementById('discovery-overlay');
    if (!overlay) return;
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('show'), 10);
    renderDiscoveryContent();
}

export function closeDiscovery() {
    const overlay = document.getElementById('discovery-overlay');
    if (!overlay) return;
    overlay.classList.remove('show');
    setTimeout(() => overlay.classList.add('hidden'), 500);
}

export function renderDiscoveryContent() {
    const content = document.getElementById('discovery-content');
    if (!content) return;

    const sections = { 'Diễn viên': new Set(), 'Studio': new Set(), 'Chủ đề': new Set() };
    const predefined = ['Học sinh / Teen', 'Show hàng / Live', 'Thủ dâm / Solo', 'Gái múp / Vú to', 'Gạ gẫm / Call sex', 'Người quen / MILF'];

    state.allVideos.forEach(v => {
        (v.categories || []).forEach(c => {
            if (c.startsWith('Diễn viên:')) sections['Diễn viên'].add(c.replace('Diễn viên: ', ''));
            else if (c.startsWith('Studio:')) sections['Studio'].add(c.replace('Studio: ', ''));
            else if (predefined.includes(c)) sections['Chủ đề'].add(c);
        });
    });

    let html = '';
    const LIMIT = 12;

    const renderSection = (title, items, renderItemFn) => {
        if (items.size === 0) return '';
        const sortedItems = Array.from(items).sort((a, b) => a.localeCompare(b, 'vi', { sensitivity: 'base' }));
        const sectionId = `section-${title.replace(/ /g, '-')}`;
        const hasMore = sortedItems.length > LIMIT;
        const visibleItems = sortedItems.slice(0, LIMIT);
        const hiddenItems = sortedItems.slice(LIMIT);

        let sectionHtml = `<div class="discovery-section"><h3 class="discovery-section-title">${escapeHtml(title)}</h3><div class="discovery-grid">`;
        sectionHtml += visibleItems.map(renderItemFn).join('');
        if (hasMore) {
            sectionHtml += `<div id="${escapeAttr(sectionId)}-hidden" class="contents hidden">`;
            sectionHtml += hiddenItems.map(renderItemFn).join('');
            sectionHtml += `</div>`;
        }
        sectionHtml += `</div>`;
        if (hasMore) {
            sectionHtml += `<button onclick="toggleDiscoverySection('${escapeInlineJsSingleQuoted(sectionId)}-hidden', this)" class="show-more-btn">Tất cả (${sortedItems.length})</button>`;
        }
        sectionHtml += `</div>`;
        return sectionHtml;
    };

    html += renderSection('Diễn viên (Idol)', sections['Diễn viên'], name => {
        const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
        const colorHue = Math.abs(name.split('').reduce((a, b) => a + b.charCodeAt(0), 0)) % 360;
        const imgPath = `/static/img/actors/${name.replace(/ /g, '_')}.jpg`;
        return `<div class="idol-avatar-container" onclick="window.selectCategory('Diễn viên: ${escapeInlineJsSingleQuoted(name)}', '${escapeInlineJsSingleQuoted(name.toUpperCase())}')">
            <div class="idol-avatar-circle" style="background: linear-gradient(135deg, hsl(${colorHue}, 60%, 40%), hsl(${colorHue}, 60%, 20%))">
                <img src="${escapeAttr(imgPath)}" class="idol-avatar-img absolute inset-0 hidden" onload="this.classList.remove('hidden')" onerror="this.style.display='none'">
                <span class="idol-avatar-initials">${escapeHtml(initials)}</span>
            </div><div class="idol-name">${escapeHtml(name)}</div></div>`;
    });

    const icons = { 'Học sinh / Teen': 'fa-graduation-cap', 'Show hàng / Live': 'fa-video', 'Thủ dâm / Solo': 'fa-hand', 'Gái múp / Vú to': 'fa-heart', 'Gạ gẫm / Call sex': 'fa-phone', 'Người quen / MILF': 'fa-user-tie' };
    html += renderSection('Khám phá chủ đề', sections['Chủ đề'], t => `<div class="category-card" onclick="window.selectCategory('${escapeInlineJsSingleQuoted(t)}', '${escapeInlineJsSingleQuoted(t.toUpperCase())}')">
        <i class="fa-solid ${icons[t] || 'fa-tags'}"></i><span>${escapeHtml(t)}</span></div>`);

    html += renderSection('Hãng phim (Studio)', sections['Studio'], s => `<div class="category-card !w-24 !h-16" onclick="window.selectCategory('Studio: ${escapeInlineJsSingleQuoted(s)}', '${escapeInlineJsSingleQuoted(s.toUpperCase())}')">
        <span class="!text-[9px]">${escapeHtml(s)}</span></div>`);

    content.innerHTML = html || '<div class="text-center py-20 text-slate-500 italic">Chưa có dữ liệu phân loại</div>';
}

export function toggleDiscoverySection(id, btn) {
    const el = document.getElementById(id);
    if (!el) return;
    const isHidden = el.classList.contains('hidden');
    if (isHidden) { el.classList.remove('hidden'); btn.innerText = 'Thu gọn'; btn.classList.add('active'); }
    else { el.classList.add('hidden'); btn.innerText = 'Xem thêm'; btn.classList.remove('active'); window.openDiscovery(); }
}
