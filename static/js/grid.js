// static/js/grid.js
import { state, saveState } from './state.js';
import { renderGrid, renderFolders, restoreScroll } from './render_service.js';
import { applyFilters, renderDynamicCategories, selectType, selectExt, selectCategory, selectSort } from './filter_service.js';
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
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        state.scrollPos = window.scrollY;
        saveState();
    }, 500);
}, { passive: true });

// Attach to window for HTML accessibility
window.applyFilters = applyFilters;
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
window.toggleDiscoverySection = toggleDiscoverySection;

export { renderGrid, renderFolders, applyFilters, restoreScroll };
