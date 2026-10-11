// Client playback quality monitor; dropped frames can include decode/network stalls.
export function createDropMonitor({ getPrefs, getCap, setCap, setStatus, fail, notify }) {
    let dropped = 0, previous = 0, sampledAt = 0, bad = 0;
    return {
        dropped: () => dropped,
        reset() { dropped = 0; previous = 0; sampledAt = 0; bad = 0; },
        sample(video) {
            if (!video.getVideoPlaybackQuality) return;
            const current = video.getVideoPlaybackQuality().droppedVideoFrames;
            if (!Number.isFinite(current)) return;
            dropped = Math.max(0, current);
            const now = performance.now();
            if (!sampledAt) { sampledAt = now; previous = current; return; }
            if (now - sampledAt < 8000) return;
            const increase = Math.max(0, current - previous);
            previous = current;
            sampledAt = now;
            bad = getPrefs().auto && increase >= 6 ? bad + 1 : 0;
            if (bad >= 2) {
                bad = 0;
                const cap = getCap();
                if (cap > 720) setCap(720);
                else if (cap > 540) setCap(540);
                else {
                    fail('Tự tắt FSR do thiết bị xem rớt quá nhiều khung hình');
                    return;
                }
                setStatus('Auto: giảm xử lý còn ' + getCap() + 'p để hạn chế giật');
            }
            notify();
        }
    };
}
