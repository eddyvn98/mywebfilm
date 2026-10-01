// static/js/security_client.js
let lastActivityPing = 0;
let statusTimer = null;
let currentInviteUrl = "";

function loginUrl(locked = false) {
    const next = window.location.pathname + window.location.search;
    const params = new URLSearchParams({ next });
    if (locked) params.set("locked", "1");
    return `/login?${params.toString()}`;
}

async function checkAuthStatus() {
    try {
        const res = await fetch("/api/auth/status", { cache: "no-store" });
        const data = await res.json();
        if (!data.authenticated) {
            window.location.replace(loginUrl(false));
            return false;
        }
        if (data.locked) {
            window.location.replace(loginUrl(true));
            return false;
        }
        return true;
    } catch {
        return true;
    }
}

async function pingActivity(force = false) {
    if (document.hidden) return;
    const now = Date.now();
    if (!force && now - lastActivityPing < 60000) return;
    lastActivityPing = now;

    try {
        const res = await fetch("/api/auth/activity", { method: "POST" });
        if (res.status === 401 || res.status === 423) {
            window.location.replace(loginUrl(true));
        }
    } catch {
        // Temporary network failures should not kick the user out.
    }
}

function formatDate(value) {
    if (!value) return "Chưa có";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Không rõ";
    return new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
    }).format(date);
}

async function loadTrustedDevices() {
    const container = document.getElementById("trusted-device-list");
    if (!container) return;
    container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center">Đang tải...</div>';

    const res = await fetch("/api/auth/devices", { cache: "no-store" });
    if (!res.ok) {
        container.innerHTML = '<div class="text-xs text-red-400 py-4 text-center">Không tải được thiết bị.</div>';
        return;
    }

    const data = await res.json();
    const devices = data.devices || [];
    container.innerHTML = devices.map(device => `
        <div class="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-key text-emerald-400 text-xs"></i>
                        <span class="text-sm font-bold text-white truncate">${escapeText(device.device_name)}</span>
                        ${device.current ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-300">Đang dùng</span>' : ''}
                    </div>
                    <div class="mt-1 text-[10px] text-slate-500">Tạo: ${formatDate(device.created_at)}</div>
                    <div class="text-[10px] text-slate-500">Dùng gần nhất: ${formatDate(device.last_used_at)}</div>
                </div>
                <div class="flex gap-1 shrink-0">
                    <button onclick="renameTrustedDevice('${device.device_id}')"
                        class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400" title="Đổi tên">
                        <i class="fa-solid fa-pen text-[10px]"></i>
                    </button>
                    <button onclick="revokeTrustedDevice('${device.device_id}', ${device.current ? "true" : "false"})"
                        class="w-8 h-8 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 ${device.current ? "opacity-40 cursor-not-allowed" : ""}"
                        title="Thu hồi Passkey" ${device.current ? "disabled" : ""}>
                        <i class="fa-solid fa-trash text-[10px]"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join("") || '<div class="text-xs text-slate-500 py-4 text-center">Chưa có thiết bị.</div>';
}

function escapeText(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
}

export function initSecurityClient() {
    ["pointerdown", "keydown", "touchstart", "scroll"].forEach(eventName => {
        window.addEventListener(eventName, () => pingActivity(false), { passive: true });
    });

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) checkAuthStatus();
    });

    pingActivity(true);
    statusTimer = window.setInterval(checkAuthStatus, 60000);
}

window.lockCinema = async () => {
    try {
        await fetch("/api/auth/lock", { method: "POST" });
    } finally {
        window.location.replace(loginUrl(true));
    }
};

window.logoutCinema = async () => {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
    } finally {
        window.location.replace("/login");
    }
};

window.openSecurityModal = async () => {
    const modal = document.getElementById("security-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    document.getElementById("device-invite-panel")?.classList.add("hidden");
    await loadTrustedDevices();
};

window.closeSecurityModal = () => {
    document.getElementById("security-modal")?.classList.add("hidden");
};

window.renameTrustedDevice = async (deviceId) => {
    const name = prompt("Tên mới cho thiết bị:");
    if (!name?.trim()) return;
    const res = await fetch(`/api/auth/devices/${encodeURIComponent(deviceId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_name: name.trim() }),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.msg || "Không đổi tên được thiết bị.");
        return;
    }
    await loadTrustedDevices();
};

window.revokeTrustedDevice = async (deviceId, isCurrent) => {
    if (isCurrent) return;
    if (!confirm("Thu hồi Passkey của thiết bị này? Thiết bị sẽ không thể đăng nhập lại nếu không được đăng ký lại.")) return;

    const res = await fetch(`/api/auth/devices/${encodeURIComponent(deviceId)}`, { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        alert(data.msg || "Không thu hồi được thiết bị.");
        return;
    }
    await loadTrustedDevices();
};

window.createDeviceInvite = async () => {
    const panel = document.getElementById("device-invite-panel");
    const qr = document.getElementById("device-invite-qr");
    const urlEl = document.getElementById("device-invite-url");
    if (!panel || !qr || !urlEl) return;

    const res = await fetch("/api/auth/bootstrap", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        alert(data.msg || "Không tạo được link đăng ký. Hãy bật Remote/Tunnel trước.");
        return;
    }

    currentInviteUrl = data.register_url;
    urlEl.value = currentInviteUrl;
    panel.classList.remove("hidden");
    qr.innerHTML = "";
    if (window.QRCode) {
        new QRCode(qr, {
            text: currentInviteUrl,
            width: 150,
            height: 150,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.H,
        });
    }
    const ttl = document.getElementById("device-invite-ttl");
    if (ttl) ttl.textContent = `Link dùng một lần · hết hạn sau ${data.expires_in} giây`;
};

window.copyDeviceInvite = async () => {
    if (!currentInviteUrl) return;
    await navigator.clipboard.writeText(currentInviteUrl);
};
