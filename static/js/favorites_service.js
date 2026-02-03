export const favoritesService = {
    favorites: [],

    async toggleFavorite(video) {
        try {
            const res = await fetch('/api/favorites/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_path: video.full_path,
                    name: video.name,
                    type: video.type
                })
            });
            const data = await res.json();
            await this.loadFavorites(); // Sync local list

            // Dispatch event for UI updates (e.g., in player or grid)
            window.dispatchEvent(new CustomEvent('favorites-updated', {
                detail: { path: video.full_path, isFavorite: data.is_favorite }
            }));

            return data.is_favorite;
        } catch (e) {
            console.error("Failed to toggle favorite:", e);
        }
    },

    async loadFavorites() {
        try {
            const res = await fetch('/api/favorites/list');
            this.favorites = await res.json();
            return this.favorites;
        } catch (e) {
            console.error("Failed to load favorites:", e);
            return [];
        }
    },

    isFavorite(path) {
        return this.favorites.some(v => v.full_path === path);
    }
};
