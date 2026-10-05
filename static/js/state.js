const STORAGE_KEY = 'mycinema_ui_state';
const SMART_MIX_MIGRATION_KEY = 'mycinema_smart_mix_default_v1';

const defaultState = {
    allVideos: [],
    currentGridVideos: [],
    currentIndex: -1,
    player: null,
    currentFolder: 'all',
    filterType: 'all',
    sortOrder: 'smart_mix',
    manageMode: false,
    selectedPaths: [],
    renamingIndex: null,
    scrollPos: 0,
    queuedPaths: [],
    filterExt: 'all',
    currentCategory: 'all',
    pageSize: 40,
    currentPage: 1
};

function loadStoredState() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            let sortOrder = parsed.sortOrder || 'smart_mix';
            if (!localStorage.getItem(SMART_MIX_MIGRATION_KEY)) {
                if (sortOrder === 'added_newest') sortOrder = 'smart_mix';
                localStorage.setItem(SMART_MIX_MIGRATION_KEY, '1');
            }
            // Only merge specific persistent fields
            return {
                ...defaultState,
                currentFolder: parsed.currentFolder || 'all',
                filterType: parsed.filterType || 'all',
                sortOrder,
                scrollPos: parsed.scrollPos || 0
            };
        }
    } catch (e) {
        console.error("Failed to load state:", e);
    }
    localStorage.setItem(SMART_MIX_MIGRATION_KEY, '1');
    return { ...defaultState };
}

export const state = loadStoredState();

export function saveState() {
    try {
        const toSave = {
            currentFolder: state.currentFolder,
            filterType: state.filterType,
            sortOrder: state.sortOrder,
            scrollPos: state.scrollPos || 0
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) {
        console.error("Failed to save state:", e);
    }
}

// Make it accessible for legacy onclick and debugging
window.state = state;
