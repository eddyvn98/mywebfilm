// static/js/gestures.js
import { state } from './state.js';
import { playNext, playPrev, closeVideoModal } from './player.js';

let gesturesInitialized = false;

function isInteractiveTarget(target) {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest(
        '#playlist-sidebar, #playlist-overlay, #drag-handle, .plyr__controls, .plyr__menu, ' +
        'button, input, select, textarea, a, [role="button"], [contenteditable="true"]'
    ));
}

function isInsidePlayerSurface(target, modal) {
    if (!(target instanceof Node)) return false;
    const player = document.querySelector('#video-modal .plyr');
    return Boolean(player?.contains(target) || modal.querySelector('.flex-1')?.contains(target));
}

export function initGestures() {
    if (gesturesInitialized) return;
    gesturesInitialized = true;

    const modal = document.getElementById('video-modal');
    const handle = document.getElementById('drag-handle');
    if (!modal || !handle) return;

    let handleStartY = 0;
    let draggingHandle = false;

    // --- SWIPE TO CLOSE (DRAG HANDLE ONLY) ---
    handle.addEventListener('touchstart', (e) => {
        if (!e.touches[0]) return;
        draggingHandle = true;
        handleStartY = e.touches[0].clientY;
        modal.style.transition = 'none';
        e.stopPropagation();
    }, { passive: true });

    handle.addEventListener('touchmove', (e) => {
        if (!draggingHandle || !e.touches[0]) return;
        const delta = e.touches[0].clientY - handleStartY;
        if (delta > 0) modal.style.transform = `translateY(${delta}px)`;
        e.stopPropagation();
    }, { passive: true });

    handle.addEventListener('touchend', (e) => {
        if (!draggingHandle || !e.changedTouches[0]) return;
        draggingHandle = false;
        modal.style.transition = 'transform 0.3s ease-in-out';

        const delta = e.changedTouches[0].clientY - handleStartY;
        if (delta > 150) {
            closeVideoModal();
        } else {
            modal.style.transform = '';
            modal.style.transition = '';
        }
        e.stopPropagation();
    });

    // --- PLAYER GESTURES ---
    let startY = 0;
    let startX = 0;
    let originalTime = 0;
    let pendingSeekTime = null;
    let trackingTouch = false;
    let trackingMouse = false;
    let isSeeking = false;
    const seekSensitivity = 0.5;

    const resetGesture = () => {
        trackingTouch = false;
        trackingMouse = false;
        isSeeking = false;
        pendingSeekTime = null;
    };

    const startAction = (clientX, clientY, target, isMouse) => {
        if (modal.classList.contains('hidden') || draggingHandle) return false;
        if (isInteractiveTarget(target)) return false;

        const isFullscreen = Boolean(
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            document.mozFullScreenElement ||
            document.msFullscreenElement
        );

        if (!isFullscreen && !isInsidePlayerSurface(target, modal)) return false;

        startX = clientX;
        startY = clientY;
        originalTime = state.player?.currentTime || 0;
        pendingSeekTime = null;
        isSeeking = false;

        if (isMouse) trackingMouse = true;
        else trackingTouch = true;
        return true;
    };

    const moveAction = (clientX, clientY, e) => {
        if (!trackingTouch && !trackingMouse) return;

        const diffX = clientX - startX;
        const diffY = clientY - startY;

        if (!isSeeking && Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 20) {
            isSeeking = true;
        }

        if (!isSeeking) return;

        if (e.cancelable) e.preventDefault();
        if (!state.player || !Number.isFinite(state.player.duration)) return;

        const nextTime = originalTime + (diffX * seekSensitivity);
        pendingSeekTime = Math.max(0, Math.min(nextTime, state.player.duration));
    };

    const endAction = (clientX, clientY) => {
        if (!trackingTouch && !trackingMouse) return;

        const diffX = startX - clientX;
        const diffY = startY - clientY;
        const wasSeeking = isSeeking;
        const seekTarget = pendingSeekTime;
        resetGesture();

        if (wasSeeking) {
            if (state.player && Number.isFinite(seekTarget)) {
                state.player.currentTime = seekTarget;
            }
            state.player?.play().catch(() => { });
            return;
        }

        // Navigation is vertical only. Horizontal movement is reserved for seeking.
        if (Math.abs(diffY) > 60 && Math.abs(diffY) > Math.abs(diffX)) {
            if (diffY > 0) playNext();
            else playPrev();
        }
    };

    window.addEventListener('mousedown', e => {
        startAction(e.clientX, e.clientY, e.target, true);
    });

    window.addEventListener('mousemove', e => {
        if (trackingMouse) moveAction(e.clientX, e.clientY, e);
    });

    window.addEventListener('mouseup', e => {
        if (trackingMouse) endAction(e.clientX, e.clientY);
    });

    window.addEventListener('touchstart', e => {
        if (!e.touches[0]) return;
        startAction(e.touches[0].clientX, e.touches[0].clientY, e.target, false);
    }, { passive: true });

    window.addEventListener('touchmove', e => {
        if (!trackingTouch || !e.touches[0]) return;
        moveAction(e.touches[0].clientX, e.touches[0].clientY, e);
    }, { passive: false });

    window.addEventListener('touchend', e => {
        if (!trackingTouch || !e.changedTouches[0]) return;
        endAction(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
    });

    window.addEventListener('touchcancel', resetGesture);

    // Wheel navigation only over the actual player surface, never over playlist/controls.
    let lastScrollTime = 0;
    window.addEventListener('wheel', e => {
        if (modal.classList.contains('hidden')) return;
        if (isInteractiveTarget(e.target) || !isInsidePlayerSurface(e.target, modal)) return;

        const now = Date.now();
        if (now - lastScrollTime < 1000 || Math.abs(e.deltaY) <= 15) return;

        lastScrollTime = now;
        if (e.deltaY > 0) playNext();
        else playPrev();
    }, { passive: true });
}
