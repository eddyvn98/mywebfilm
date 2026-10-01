// static/js/grid.js
import { state, saveState } from './state.js';
import { renderGrid, renderFolders, restoreScroll } from './render_service.js';
import { applyFilters, renderDynamicCategories, selectType, selectExt, selectCategory, selectSort, filterByFavorites, filterByHistory } from './filter_service.js';

export { renderGrid, renderFolders, restoreScroll, applyFilters, renderDynamicCategories, selectType, selectExt, selectCategory, selectSort, filterByFavorites, filterByHistory };
import {
    toggleManageMode, handleCardClick, toggleSelection, updateSelectionUI,
    processHighlight, clearCompletedQueue, cancelSelection,
    openRenameModal, closeRenameModal, confirmRename,
    bulkDelete, bulkMove, filterByFolder, handlePreview,
    showInfo, deleteItem
} from './manage_service.js';
import { openDiscovery, closeDiscovery, renderDiscoveryContent, toggleDiscoverySection } from './discovery_service.js';

// Global Event Listeners logic that belongs to grid entry point
document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown')) {
        document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
    }
});

let scrollTimeout;
window.addEventListener('scroll', () => {
    // Show/Hide Back to Top button
    const btn = document.getElementById('back-to-top');
    if (btn) {
        if (window.scrollY > 500) {
            btn.classList.add('translate-y-0', 'opacity-100');
            btn.classList.remove('translate-y-24', 'opacity-0');
        } else {
            btn.classList.add('translate-y-24', 'opacity-0');
            btn.classList.remove('translate-y-0', 'opacity-100');
        }
    }

    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        state.scrollPos = window.scrollY;
        saveState();
    }, 500);
}, { passive: true });

// Attach to window for HTML accessibility
let searchFilterTimeout = null;
window.applyFilters = (...args) => {
    clearTimeout(searchFilterTimeout);
    searchFilterTimeout = setTimeout(() => {
        searchFilterTimeout = null;
        applyFilters(...args);
    }, 180);
};
window.renderFolders = renderFolders;
window.toggleManageMode = toggleManageMode;
window.handleCardClick = handleCardClick;
window.toggleSelection = toggleSelection;
window.processHighlight = processHighlight;
window.clearCompletedQueue = clearCompletedQueue;
window.cancelSelection = cancelSelection;
window.openRenameModal = openRenameModal;
window.closeRenameModal = closeRenameModal;
window.confirmRename = confirmRename;
window.bulkDelete = bulkDelete;
window.bulkMove = bulkMove;
window.filterByFolder = filterByFolder;
window.handlePreview = handlePreview;
window.showInfo = showInfo;
window.deleteItem = deleteItem;
window.handleFavoriteToggle = async (e, idx) => {
    e.stopPropagation();
    const video = state.currentGridVideos[idx];
    if (!video) return;

    // Toggle
    const { favoritesService } = await import('./favorites_service.js');
    await favoritesService.toggleFavorite(video);

    // Re-render only this card or grid? 
    // Grid re-render is safer for crosshair/state consistency
    renderGrid(state.currentGridVideos, false, false);
};
window.toggleDropdown = (id) => {
    const menu = document.getElementById(id)?.querySelector('.dropdown-menu');
    const isShowing = menu?.classList.contains('show');
    document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
    if (menu && !isShowing) menu.classList.add('show');
};
window.selectType = selectType;
window.selectExt = selectExt;
window.selectCategory = selectCategory;
window.selectSort = selectSort;
window.handleBadgeClick = (e, val, label) => { e.stopPropagation(); selectCategory(val, label); };
window.openDiscovery = openDiscovery;
window.closeDiscovery = closeDiscovery;
window.filterByFavorites = filterByFavorites;
window.filterByHistory = filterByHistory;
window.toggleDiscoverySection = toggleDiscoverySection;
