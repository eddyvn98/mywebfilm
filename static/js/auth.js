// static/js/auth.js
import { state } from './state.js';

export function checkPinStatus() {
    state.pinOverlay = document.getElementById('pin-overlay');
    const isAuth = sessionStorage.getItem('cinema_authenticated');
    if (isAuth === 'true') {
        state.pinOverlay.classList.add('hidden');
    } else {
        state.pinOverlay.classList.remove('hidden');
    }
}

export function pressPin(num) {
    if (state.currentPinInput.length >= 4) return;
    state.currentPinInput += num;
    updatePinDots();
    if (state.currentPinInput.length === 4) {
        setTimeout(verifyPin, 200);
    }
}

export function updatePinDots() {
    const dots = document.querySelectorAll('#pin-dots > div');
    dots.forEach((dot, i) => {
        if (i < state.currentPinInput.length) {
            dot.classList.add('bg-blue-500', 'border-blue-500');
            dot.classList.remove('border-slate-700');
        } else {
            dot.classList.remove('bg-blue-500', 'border-blue-500');
            dot.classList.add('border-slate-700');
        }
    });
}

export function clearPin() {
    state.currentPinInput = '';
    updatePinDots();
}

export function verifyPin() {
    if (state.currentPinInput === state.correctPin) {
        sessionStorage.setItem('cinema_authenticated', 'true');
        if (window.loadLibrary) window.loadLibrary(); // Start loading the heavy stuff now
        state.pinOverlay.classList.add('opacity-0');
        setTimeout(() => {
            state.pinOverlay.classList.add('hidden');
            state.pinOverlay.classList.remove('opacity-0');
        }, 300);
    } else {
        const error = document.getElementById('pin-error');
        error.classList.remove('opacity-0');
        state.currentPinInput = '';
        updatePinDots();
        setTimeout(() => {
            error.classList.add('opacity-0');
        }, 2000);
    }
}

// Expose to window for inline onclicks
window.pressPin = pressPin;
window.clearPin = clearPin;
window.verifyPin = verifyPin;
