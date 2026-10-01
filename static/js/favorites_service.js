export const favoritesService = {
    favorites: [],
    favoritePaths: new Set(),

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
            this.favoritePaths = new Set(this.favorites.map(v => v.full_path));
            return this.favorites;
        } catch (e) {
            console.error("Failed to load favorites:", e);
            this.favorites = [];
            this.favoritePaths = new Set();
            return [];
        }
    },

    isFavorite(path) {
        return this.favoritePaths.has(path);
    }
};
