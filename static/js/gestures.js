// static/js/gestures.js
import { state } from './state.js';
import { playNext, playPrev, closeVideoModal } from './player.js';

let gesturesInitialized = false;

export function initGestures() {
    if (gesturesInitialized) return;
    gesturesInitialized = true;

    const modal = document.getElementById('video-modal');
    const handle = document.getElementById('drag-handle');
    const container = document.querySelector('#video-modal > div.flex-1');
    let handleStartY = 0;

    // --- SWIPE TO CLOSE (DRAG HANDLE) ---
    handle.addEventListener('touchstart', (e) => {
        handleStartY = e.touches[0].clientY;
        modal.style.transition = 'none';
    }, { passive: false });

    handle.addEventListener('touchmove', (e) => {
        const delta = e.touches[0].clientY - handleStartY;
        if (delta > 0) modal.style.transform = `translateY(${delta}px)`;
    }, { passive: false });

    handle.addEventListener('touchend', (e) => {
        modal.style.transition = 'transform 0.3s ease-in-out';
        if (e.changedTouches[0].clientY - handleStartY > 150) closeVideoModal();
        else modal.style.transform = 'translateY(0)';
    });

    // --- NAVIGATION & SEEKING (GLOBAL Handlers for Fullscreen Support) ---
    let navStartY = 0, navStartX = 0, isSeeking = false, isMouseDown = false, originalTime = 0;
    const seekSensitivity = 0.5;

    const startAction = (clientX, clientY, isMouse, target) => {
        if (modal.classList.contains('hidden')) return;
        // Only start if clicking on modal or if in fullscreen
        const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
        if (!isFullscreen && !modal.contains(target)) return;

        navStartY = clientY; navStartX = clientX; isSeeking = false;
        if (isMouse) isMouseDown = true;
        if (state.player) originalTime = state.player.currentTime;
    };

    const moveAction = (clientX, clientY, e) => {
        if (modal.classList.contains('hidden')) return;
        if (!isMouseDown && e.type !== 'touchmove') return;

        if (isSeeking) {
            if (e.cancelable) e.preventDefault();
            const diffX = clientX - navStartX;
            if (state.player && state.player.duration) {
                let newTime = originalTime + (diffX * seekSensitivity);
                state.player.currentTime = Math.max(0, Math.min(newTime, state.player.duration));
            }
            return;
        }

        // Determine if seeking (heavy horizontal movement)
        if (Math.abs(navStartX - clientX) > Math.abs(navStartY - clientY) && Math.abs(navStartX - clientX) > 20) {
            isSeeking = true;
        }
    };

    const endAction = (clientX, clientY) => {
        if (modal.classList.contains('hidden')) {
            isMouseDown = false;
            return;
        }

        if (!isMouseDown && !isSeeking && Math.abs(navStartY - clientY) < 10 && Math.abs(navStartX - clientX) < 10) return;
        isMouseDown = false;

        if (isSeeking) {
            isSeeking = false;
            state.player?.play().catch(() => { });
            return;
        }

        // NAVIGATION: Support both Vertical and Horizontal
        const diffX = navStartX - clientX;
        const diffY = navStartY - clientY;

        // Try Vertical Swipe first
        if (Math.abs(diffY) > 60 && Math.abs(diffX) < 100) {
            if (diffY > 0) playNext();
            else playPrev();
        }
        // Then Horizontal Swipe
        else if (Math.abs(diffX) > 60 && Math.abs(diffY) < 100) {
            if (diffX > 0) playNext();
            else playPrev();
        }
    };

    // Attach to window to support Fullscreen
    window.addEventListener('mousedown', e => {
        if (modal.classList.contains('hidden')) return;
        startAction(e.clientX, e.clientY, true, e.target);
    });

    window.addEventListener('touchstart', e => {
        if (modal.classList.contains('hidden')) return;
        startAction(e.touches[0].clientX, e.touches[0].clientY, false, e.target);
    }, { passive: true });

    window.addEventListener('mousemove', e => { if (isMouseDown) moveAction(e.clientX, e.clientY, e); });
    window.addEventListener('mouseup', e => { if (isMouseDown) endAction(e.clientX, e.clientY); });

    window.addEventListener('touchmove', e => {
        if (isMouseDown || e.touches.length > 0) {
            moveAction(e.touches[0].clientX, e.touches[0].clientY, e);
        }
    }, { passive: false });

    window.addEventListener('touchend', e => {
        if (e.changedTouches && e.changedTouches[0]) {
            endAction(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
        }
    });

    // Wheel (Mouse Scroll) - Global for Fullscreen
    let lastScrollTime = 0;
    window.addEventListener('wheel', e => {
        if (modal.classList.contains('hidden')) return;

        // If not fullscreen, only scroll if mouse is over modal
        const isFullscreen = document.fullscreenElement !== null;
        if (!isFullscreen && !modal.contains(e.target)) return;

        const now = Date.now();
        if (now - lastScrollTime < 1000) return;

        if (Math.abs(e.deltaY) > 15) {
            lastScrollTime = now;
            if (e.deltaY > 0) playNext();
            else playPrev();
        }
    }, { passive: true });

    // Keyboard
    window.addEventListener('keydown', e => {
        if (modal.classList.contains('hidden')) return;
        if (['ArrowUp', 'ArrowDown'].includes(e.key)) e.preventDefault();
        if (e.key === 'ArrowUp') playPrev();
        if (e.key === 'ArrowDown') playNext();
        if (e.key === 'Escape') closeVideoModal();
    });
}
