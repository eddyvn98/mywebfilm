// Keep filenames aligned with actor_image_store.actor_image_filename on the server.
export function actorPhotoUrl(name) {
    if (typeof name !== 'string') return 'data:,';
    let stem = name.normalize('NFKC').trim();
    if (!stem || /[\\/]/.test(stem)) return 'data:,';
    if (/\.jpg$/i.test(stem)) stem = stem.slice(0, -4);
    stem = stem.replace(/\s+/g, '_').replace(/[<>:"/\\|?*\x00-\x1f]/g, '_');
    stem = stem.slice(0, 80).replace(/^[ .]+|[ .]+$/g, '');
    if (!stem || /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(stem)) {
        return 'data:,';
    }
    return `/api/actor_image/${encodeURIComponent(stem + '.jpg')}`;
}
