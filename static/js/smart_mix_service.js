const VISIT_KEY = 'mycinema_smart_mix_visit_v1';

let activeSeed = 1;

function normalize(value) {
    return String(value || '').trim().toLowerCase();
}

function hashString(value) {
    let hash = 2166136261;
    const text = String(value || '');
    for (let i = 0; i < text.length; i += 1) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
}

function seededFraction(value, seed = activeSeed) {
    return (hashString(`${seed}:${value}`) % 10000) / 10000;
}

function pushSignal(target, seen, type, value, weight) {
    const clean = normalize(value);
    if (!clean) return;
    const key = `${type}:${clean}`;
    if (seen.has(key)) return;
    seen.add(key);
    target.push({ key, type, value: clean, weight });
}

export function getMetadataSignals(video) {
    const meta = video?.jav_metadata || {};
    const signals = [];
    const seen = new Set();

    for (const actor of meta.actors || []) pushSignal(signals, seen, 'actor', actor, 6);
    pushSignal(signals, seen, 'series', meta.series, 5);
    for (const genre of meta.genres || []) pushSignal(signals, seen, 'genre', genre, 4);
    pushSignal(signals, seen, 'studio', meta.studio, 3);
    pushSignal(signals, seen, 'label', meta.label, 2);

    for (const category of video?.categories || []) {
        const text = String(category || '').trim();
        if (!text) continue;
        if (text.startsWith('Diễn viên:')) {
            pushSignal(signals, seen, 'actor', text.slice('Diễn viên:'.length), 6);
        } else if (text.startsWith('Studio:')) {
            pushSignal(signals, seen, 'studio', text.slice('Studio:'.length), 3);
        } else {
            pushSignal(signals, seen, 'category', text, 1.5);
        }
    }

    return signals;
}

export function beginSmartMixVisit() {
    let visit = Number.parseInt(localStorage.getItem(VISIT_KEY) || '0', 10);
    if (!Number.isFinite(visit)) visit = 0;
    activeSeed = (visit + 1) % 1000000 || 1;
    localStorage.setItem(VISIT_KEY, String(activeSeed));
    return activeSeed;
}

export function advanceSmartMixVisit() {
    return beginSmartMixVisit();
}

export function getSmartMixSeed() {
    return activeSeed;
}

function buildPreferenceMaps(videos, favoritePaths, historyPaths) {
    const favoriteSet = favoritePaths instanceof Set
        ? favoritePaths
        : new Set(favoritePaths || []);
    const historyIndex = new Map((historyPaths || []).map((path, index) => [path, index]));
    const itemPreference = new Map();
    const signalPreference = new Map();

    for (const video of videos) {
        const path = video.full_path;
        let preference = favoriteSet.has(path) ? 4 : 0;
        if (historyIndex.has(path)) {
            const index = historyIndex.get(path);
            preference += Math.max(0.6, 3 - (index * 0.12));
        }
        itemPreference.set(path, preference);
        if (preference <= 0) continue;

        for (const signal of getMetadataSignals(video)) {
            const boost = preference * (signal.weight / 6);
            signalPreference.set(
                signal.key,
                (signalPreference.get(signal.key) || 0) + boost
            );
        }
    }

    return { itemPreference, signalPreference };
}

function buildGroups(videos, signalPreference) {
    const groups = new Map();

    for (const video of videos) {
        for (const signal of getMetadataSignals(video)) {
            let group = groups.get(signal.key);
            if (!group) {
                group = { ...signal, videos: [] };
                groups.set(signal.key, group);
            }
            group.videos.push(video);
        }
    }

    return [...groups.values()]
        .filter(group => group.videos.length >= 2)
        .map(group => ({
            ...group,
            preference: signalPreference.get(group.key) || 0,
            rank:
                (group.weight * 1.8)
                + Math.min(group.videos.length, 12) * 0.08
                + (signalPreference.get(group.key) || 0) * 1.35
                + seededFraction(group.key) * 3.2,
        }))
        .sort((a, b) => b.rank - a.rank)
        .slice(0, 28);
}

function scoreVideo(video, itemPreference, groupKey) {
    const preference = itemPreference.get(video.full_path) || 0;
    const release = String(video.jav_metadata?.release_date || '');
    const releaseYear = Number.parseInt(release.slice(0, 4), 10);
    const freshness = Number.isFinite(releaseYear)
        ? Math.min(1, Math.max(0, releaseYear - 2015) / 12)
        : 0;
    return (
        preference * 2.8
        + freshness * 0.7
        + seededFraction(`${groupKey}:${video.full_path}`) * 2.5
    );
}

function sortedBucket(group, itemPreference) {
    return [...group.videos].sort((a, b) =>
        scoreVideo(b, itemPreference, group.key)
        - scoreVideo(a, itemPreference, group.key)
    );
}

function buildExplorationPool(videos, selected, itemPreference) {
    return videos
        .filter(video => !selected.has(video.full_path))
        .sort((a, b) => {
            const prefDiff = (itemPreference.get(a.full_path) || 0)
                - (itemPreference.get(b.full_path) || 0);
            if (prefDiff !== 0) return prefDiff;
            return seededFraction(a.full_path) - seededFraction(b.full_path);
        });
}

export function buildSmartMix(videos, options = {}) {
    if (!Array.isArray(videos) || videos.length < 3) return [...(videos || [])];

    const { favoritePaths = [], historyPaths = [] } = options;
    const { itemPreference, signalPreference } = buildPreferenceMaps(
        videos,
        favoritePaths,
        historyPaths
    );
    const groups = buildGroups(videos, signalPreference);

    if (!groups.length) {
        const offset = activeSeed % videos.length;
        return [...videos.slice(offset), ...videos.slice(0, offset)];
    }

    const buckets = groups.map(group => ({
        group,
        items: sortedBucket(group, itemPreference),
        cursor: 0,
    }));
    const output = [];
    const selected = new Set();
    let exploration = buildExplorationPool(videos, selected, itemPreference);
    let explorationCursor = 0;
    let pass = 0;

    const takeNextFromBucket = bucket => {
        while (bucket.cursor < bucket.items.length) {
            const candidate = bucket.items[bucket.cursor++];
            if (selected.has(candidate.full_path)) continue;
            selected.add(candidate.full_path);
            output.push(candidate);
            return true;
        }
        return false;
    };

    while (output.length < videos.length) {
        let addedThisPass = false;
        const rotated = buckets.slice(pass % buckets.length)
            .concat(buckets.slice(0, pass % buckets.length));

        for (const bucket of rotated) {
            if (takeNextFromBucket(bucket)) addedThisPass = true;
            if (output.length >= videos.length) break;

            if (output.length > 0 && output.length % 5 === 0) {
                exploration = buildExplorationPool(videos, selected, itemPreference);
                explorationCursor = 0;
                while (explorationCursor < exploration.length) {
                    const candidate = exploration[explorationCursor++];
                    if (selected.has(candidate.full_path)) continue;
                    selected.add(candidate.full_path);
                    output.push(candidate);
                    addedThisPass = true;
                    break;
                }
            }
        }

        if (!addedThisPass) break;
        pass += 1;
    }

    const remaining = videos
        .filter(video => !selected.has(video.full_path))
        .sort((a, b) => seededFraction(a.full_path) - seededFraction(b.full_path));

    return output.concat(remaining);
}
