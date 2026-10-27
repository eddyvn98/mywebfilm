// Keep filenames aligned with actor_image_store.actor_image_filename on the server.
export function actorPhotoUrl(name) {
    if (typeof name !== 'string') return 'data:,';
    let stem = name.normalize('NFKC').trim();
    if (!stem || stem.includes('/') || stem.includes('\\')) return 'data:,';
    if (/\.jpg$/i.test(stem)) stem = stem.slice(0, -4);
    stem = stem.replace(/\s+/g, '_');
    const forbidden = '<>:"/\\|?*';
    stem = Array.from(stem, ch =>
        forbidden.includes(ch) || ch.codePointAt(0) < 32 ? '_' : ch
    ).slice(0, 80).join('').replace(/^[ .]+|[ .]+$/g, '');
    if (!stem || /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(stem)) {
        return 'data:,';
    }
    return '/api/actor_image/' + encodeURIComponent(stem + '.jpg');
}
