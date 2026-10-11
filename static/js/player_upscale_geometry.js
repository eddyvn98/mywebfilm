// Calculate the WebGL drawing-buffer resolution in physical (Retina) pixels.
// Budget remains configurable: 1080p initially, 1440p/4K when selected.
export function targetFsrSize({ videoWidth, videoHeight, cssWidth, cssHeight, dpr = 1, cap = 1080 }) {
    const w = Number(videoWidth), h = Number(videoHeight);
    const vw = Number(cssWidth), vh = Number(cssHeight);
    if (![w, h, vw, vh].every(n => Number.isFinite(n) && n > 0)) {
        return { kind: 'waiting', width: 0, height: 0, dpr: 1 };
    }
    const density = Number.isFinite(Number(dpr))
        ? Math.max(1, Math.min(3, Number(dpr))) : 1;
    const targetRatio = Math.min(vw * density / w, vh * density / h);
    // FSR EASU is an upscaler, not a downscaler. Keep native video on shrink.
    if (targetRatio < 0.995) {
        return { kind: 'native', width: w, height: h, dpr: density,
            reason: 'Video gốc đã lớn hơn vùng hiển thị thực tế' };
    }
    const maxPixels = 1920 * 1080 * Math.pow(Number(cap) / 1080, 2);
    if (!Number.isFinite(maxPixels) || maxPixels < w * h * 0.98) {
        return { kind: 'native', width: w, height: h, dpr: density,
            reason: 'Giới hạn độ phân giải thấp hơn video gốc' };
    }
    const budgetRatio = Math.sqrt(maxPixels / (w * h));
    const scale = Math.max(1, Math.min(targetRatio, budgetRatio));
    const width = Math.max(2, Math.round(w * scale));
    const height = Math.max(2, Math.round(h * scale));
    return { kind: scale > 1.001 ? 'upscale' : 'sharpen',
        width, height, dpr: density };
}
