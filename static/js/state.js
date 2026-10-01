const STORAGE_KEY = 'mycinema_ui_state';

const defaultState = {
    allVideos: [],
    currentGridVideos: [],
    currentIndex: -1,
    player: null,
    currentFolder: 'all',
    filterType: 'all',
    sortOrder: 'added_newest',
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
            // Only merge specific persistent fields
            return {
                ...defaultState,
                currentFolder: parsed.currentFolder || 'all',
                filterType: parsed.filterType || 'all',
                sortOrder: parsed.sortOrder || 'added_newest',
                scrollPos: parsed.scrollPos || 0
            };
        }
    } catch (e) {
        console.error("Failed to load state:", e);
    }
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
