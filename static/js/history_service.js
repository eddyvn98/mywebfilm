import { getThumbnailUrl } from './api.js';

export const historyService = {
    async addToHistory(video) {
        try {
            await fetch('/api/history/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_path: video.full_path,
                    name: video.name,
                    type: video.type
                })
            });
            this.loadHistory(); // Refresh UI if on home
        } catch (e) {
            console.error("Failed to add to history:", e);
        }
    },

    async loadHistoryData() {
        try {
            const res = await fetch('/api/history/list');
            this.historyData = await res.json();
        } catch (e) {
            console.error("Failed to load history data:", e);
            this.historyData = [];
        }
    },

    getHistoryPaths() {
        return (this.historyData || []).map(v => v.full_path);
    }
};

window.historyService = historyService;

window.playHistoryItem = async (path, type) => {
    // We need to find the video object in the master list or just play by path
    // For simplicity, we search the state.allVideos or just trigger a refresh/play
    // Actually, usually history items are in the current library.
    // Let's use search logic to find and play.
    const url = `/api/stream?path=${encodeURIComponent(path)}`;
    // But we want to use the modal. We'll need a way to play specific path via player.js
    // For now, let's just trigger window.openVideoByPath if we implement it.
    // Better: dispatch a custom event or call window.playStreamByPath
    if (window.playByPath) {
        window.playByPath(path, type);
    }
};
