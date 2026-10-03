const SCAN_POLL_MS = 700;
const SCAN_MAX_WAIT_MS = 30 * 60 * 1000;

export async function runLibraryScan() {
    const response = await fetch('/api/scan', { method: 'POST' });
    if (!response.ok) {
        throw new Error(`Không thể bắt đầu scan (HTTP ${response.status})`);
    }

    const started = await response.json();
    if (started.scan?.status === 'failed') {
        throw new Error(started.scan.error || 'Scan thất bại');
    }

    const deadline = Date.now() + SCAN_MAX_WAIT_MS;
    while (Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, SCAN_POLL_MS));
        const statusResponse = await fetch('/api/scan/status', { cache: 'no-store' });
        if (!statusResponse.ok) {
            throw new Error(`Không thể đọc trạng thái scan (HTTP ${statusResponse.status})`);
        }

        const status = await statusResponse.json();
        if (status.status === 'done' || status.status === 'idle') {
            return status;
        }
        if (status.status === 'failed') {
            throw new Error(status.error || 'Scan thất bại');
        }
    }

    throw new Error('Scan quá lâu và đã vượt thời gian chờ của giao diện');
}
