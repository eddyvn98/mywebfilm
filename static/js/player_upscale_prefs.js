// Persisted, validated video upscaling preferences (no API or token required).
const KEY = 'cinema_upscale_settings_v1';
const DEFAULTS = Object.freeze({
    source: 'browser', preset: 'off', strength: 50, cap: 1080, auto: true
});
const SOURCES = new Set(['browser', 'server']);
const PRESETS = new Set(['off', 'balanced', 'sharp', 'custom']);
const CAPS = new Set([720, 1080, 1440, 2160]);
let preferences = { ...DEFAULTS };
try {
    const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (saved && typeof saved === 'object') preferences = validate(saved);
    else {
        const legacy = localStorage.getItem('cinema_upscale_mode');
        if (PRESETS.has(legacy)) preferences.preset = legacy;
    }
} catch {}

export function validate(values) {
    const next = { ...DEFAULTS };
    if (SOURCES.has(values.source)) next.source = values.source;
    if (PRESETS.has(values.preset)) next.preset = values.preset;
    if (Number.isFinite(Number(values.strength))) {
        next.strength = Math.max(0, Math.min(100, Math.round(Number(values.strength))));
    }
    if (CAPS.has(Number(values.cap))) next.cap = Number(values.cap);
    if (typeof values.auto === 'boolean') next.auto = values.auto;
    return next;
}
export function getUpscalePrefs() { return { ...preferences }; }
export function saveUpscalePrefs(changes) {
    preferences = validate({ ...preferences, ...changes });
    try { localStorage.setItem(KEY, JSON.stringify(preferences)); } catch {}
    return getUpscalePrefs();
}
export function rcasStops(preset = preferences.preset) {
    if (preset === 'sharp') return 0.15;
    if (preset === 'balanced') return 1.5;
    return 2 * (1 - preferences.strength / 100);
}
