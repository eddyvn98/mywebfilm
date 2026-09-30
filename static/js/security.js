export function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

export function escapeAttr(value) {
    return escapeHtml(value);
}

export function escapeInlineJsSingleQuoted(value) {
    const jsSafe = String(value ?? '')
        .replaceAll('\\', '\\\\')
        .replaceAll("'", "\\'")
        .replaceAll('\r', '\\r')
        .replaceAll('\n', '\\n')
        .replaceAll('\u2028', '\\u2028')
        .replaceAll('\u2029', '\\u2029');
    return escapeAttr(jsSafe);
}
