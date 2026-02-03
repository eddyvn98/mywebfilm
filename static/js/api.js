// static/js/api.js
export async function fetchConfig() {
    const res = await fetch('/api/config');
    return await res.json();
}

export async function apiUpdateConfig(updates) {
    return fetch('/api/config/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    }).then(r => r.json());
}

export async function fetchVideos() {
    const res = await fetch('/api/videos');
    return await res.json();
}

export function getStreamUrl(path) {
    return `/api/stream?path=${encodeURIComponent(path)}`;
}

export function getPreviewUrl(path) {
    return `/api/preview?path=${encodeURIComponent(path)}`;
}

export function getThumbnailUrl(path, type) {
    return `/api/thumbnail?path=${encodeURIComponent(path)}&type=${type}`;
}

export async function playOnServer(path, type) {
    return fetch('/api/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, type })
    });
}

export async function apiAddFolder(path) {
    return fetch('/api/add_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
}

export async function apiRemoveFolder(path) {
    return fetch('/api/remove_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
}

export async function deleteFile(path) {
    return fetch('/api/delete_file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
}

export async function openExplorer(path) {
    return fetch('/api/explorer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
}

export async function apiRename(oldPath, newName) {
    const res = await fetch('/api/fs/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_path: oldPath, new_name: newName })
    });
    return await res.json();
}

export async function apiMkdir(parentPath, name) {
    const res = await fetch('/api/fs/mkdir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_path: parentPath, name: name })
    });
    return await res.json();
}

export async function apiMove(paths, targetDir) {
    const res = await fetch('/api/fs/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths, target_dir: targetDir })
    });
    return await res.json();
}

export async function apiProcessHighlight(path) {
    const res = await fetch('/api/process/highlight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
    });
    return await res.json();
}

export async function apiAddQueue(paths) {
    console.log("apiAddQueue called with:", paths);
    const res = await fetch('/api/process/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths })
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Lỗi server");
    }
    return await res.json();
}

export async function apiProcessConvert(paths) {
    const res = await fetch('/api/process/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths, type: 'convert' })
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Lỗi server");
    }
    return await res.json();
}

export async function apiGetQueueStatus() {
    const res = await fetch('/api/process/status');
    return await res.json();
}

export async function apiClearQueue() {
    return fetch('/api/process/clear', { method: 'POST' });
}
