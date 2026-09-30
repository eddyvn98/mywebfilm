// static/js/ai_mgmt_service.js
import { state } from './state.js';
import { renderMgmtSidebars, renderActorQuickSelect } from './mgmt_ui_service.js';

export let allTags = { genres: [], actors: [], studios: [] };

export async function loadAllTags() {
    try {
        const res = await fetch('/api/tags');
        allTags = await res.json();
        renderMgmtSidebars();
        renderActorQuickSelect();
        loadScrapperConfig();
    } catch (err) {
        console.error("Failed to load tags:", err);
    }
}

export async function loadScrapperConfig() {
    try {
        const res = await fetch('/api/config');
        const cfg = await res.json();
        const cookieEl = document.getElementById('mgmt-cookies');
        if (cookieEl) {
            cookieEl.value = "";
            cookieEl.placeholder = cfg.scrapper_cookies_configured
                ? "Đã cấu hình cookie — nhập giá trị mới để thay"
                : "Chưa cấu hình cookie";
        }
    } catch (err) {
        console.error("Failed to load config:", err);
    }
}

export async function saveScrapperCookies() {
    const val = document.getElementById('mgmt-cookies').value.trim();
    const btn = document.getElementById('btn-save-cookies');
    const originalText = btn.innerText;

    btn.disabled = true;
    btn.innerText = 'ĐANG LƯU...';

    try {
        const res = await fetch('/api/config/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scrapper_cookies: val })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            btn.innerText = 'ĐÃ LƯU THÀNH CÔNG!';
            btn.classList.add('bg-green-600');
            setTimeout(() => {
                btn.innerText = originalText;
                btn.classList.remove('bg-green-600');
                btn.disabled = false;
            }, 2000);
        } else {
            alert("Lỗi: " + (data.msg || "Không rõ"));
            btn.disabled = false;
            btn.innerText = originalText;
        }
    } catch (err) {
        alert("Lỗi kết nối: " + err.message);
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

export async function runAiAnalyzeMgmt(mgmtListVisible) {
    const file = mgmtListVisible[state.mgmtSelectedIndex];
    if (!file) return;

    const btn = document.getElementById('btn-run-ai-mgmt');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> ĐANG PHÂN TÍCH...';

    try {
        const res = await fetch('/api/ai/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name + "." + file.ext.toLowerCase() })
        });
        const data = await res.json();
        console.log("AI Data Response:", data);
        const r = data.result;

        if (r) {
            if (r.title) document.getElementById('mgmt-title').value = r.title;
            if (r.code) document.getElementById('mgmt-code').value = r.code;
            if (r.studio) document.getElementById('mgmt-studio').value = r.studio;
            if (r.actors) document.getElementById('mgmt-actors').value = r.actors.join(', ');
            if (r.genres) document.getElementById('mgmt-genres').value = r.genres.join(', ');

            // Thông báo nếu context trống
            if (!data.context || data.context.includes("Không tìm thấy")) {
                console.warn("AI warning: No web context found, results might be inaccurate.");
            }
        } else {
            // Hiển thị lỗi từ backend nếu có
            const errorMsg = data.raw_response || "AI không trả về kết quả hợp lệ.";
            alert("Lỗi AI: " + errorMsg);
        }
    } catch (err) {
        alert("Lỗi kết nối AI: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

export function parseJsonMetadata() {
    const input = document.getElementById('mgmt-json-input');
    if (!input || !input.value.trim()) {
        alert("Vui lòng nhập JSON vào ô trống!");
        return;
    }

    try {
        const data = JSON.parse(input.value);
        if (data.title) document.getElementById('mgmt-title').value = data.title;
        if (data.code) document.getElementById('mgmt-code').value = data.code;
        if (data.studio) document.getElementById('mgmt-studio').value = data.studio;

        if (data.actors) {
            const actors = Array.isArray(data.actors) ? data.actors : [data.actors];
            document.getElementById('mgmt-actors').value = actors.join(', ');
        }

        if (data.genres) {
            const genres = Array.isArray(data.genres) ? data.genres : [data.genres];
            document.getElementById('mgmt-genres').value = genres.join(', ');
        }

        renderMgmtSidebars();
        renderActorQuickSelect();
    } catch (e) {
        alert("Lỗi JSON không hợp lệ: " + e.message);
    }
}

export async function finalizeMetadata(mgmtListVisible, callbacks) {
    const file = mgmtListVisible[state.mgmtSelectedIndex];
    if (!file) return;

    const btn = document.getElementById('btn-finalize');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> ĐANG THỰC THI...';

    const metadata = {
        title: document.getElementById('mgmt-title').value.trim(),
        code: document.getElementById('mgmt-code').value.trim(),
        studio: document.getElementById('mgmt-studio').value.trim(),
        actors: document.getElementById('mgmt-actors').value.split(',').map(s => s.trim()).filter(Boolean),
        genres: document.getElementById('mgmt-genres').value.split(',').map(s => s.trim()).filter(Boolean)
    };

    const shouldRename = document.getElementById('mgmt-rename').checked;

    try {
        const res = await fetch('/api/ai/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: file.name + "." + file.ext.toLowerCase(),
                path: file.full_path,
                metadata: metadata,
                rename: shouldRename
            })
        });
        const data = await res.json();

        if (data.status === 'ok') {
            state.mgmtList.splice(state.mgmtList.findIndex(v => v.full_path === file.full_path), 1);
            state.mgmtSelectedIndex = null;
            if (callbacks.onSuccess) callbacks.onSuccess();
            alert("Hoàn tất! Metadata đã được chèn và file đã được chuẩn hóa.");
        } else {
            alert("Lỗi: " + data.msg);
        }
    } catch (err) {
        alert("Lỗi: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

export async function uploadActorImage(name, input) {
    if (!input.files || !input.files[0]) return;

    const formData = new FormData();
    formData.append('image', input.files[0]);
    formData.append('name', name);

    try {
        const res = await fetch('/api/admin/upload_actor_image', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.status === 'ok') {
            renderMgmtSidebars();
        } else {
            alert("Lỗi upload: " + (data.msg || "Không rõ"));
        }
    } catch (err) {
        alert("Lỗi kết nối: " + err.message);
    }
}
