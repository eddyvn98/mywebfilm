import { state } from './state.js';
import { getStreamUrl } from './api.js';

export function openImageModal(idx) {
    state.currentIndex = idx;
    const v = state.currentGridVideos[idx];
    if (!v) return;

    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image-img');
    const title = document.getElementById('image-modal-title');

    // Reset animation classes if any
    img.classList.remove('opacity-0', 'scale-90', 'translate-x-10', '-translate-x-10');

    title.textContent = v.name;
    img.src = getStreamUrl(v.full_path);

    modal.classList.remove('hidden');
    document.documentElement.classList.add('media-modal-open');
    setTimeout(() => modal.classList.add('opacity-100'), 10);

    // Add Wheel Event for navigation
    window.addEventListener('wheel', handleImageWheel, { passive: false });
}

export function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('opacity-100');
    setTimeout(() => {
        modal.classList.add('hidden');
        document.getElementById('modal-image-img').src = '';
    }, 300);
    window.removeEventListener('wheel', handleImageWheel);
    document.documentElement.classList.remove('media-modal-open');
}

let lastWheelTime = 0;
async function handleImageWheel(e) {
    const modal = document.getElementById('image-modal');
    if (modal.classList.contains('hidden')) return;

    e.preventDefault();
    const now = Date.now();
    if (now - lastWheelTime < 600) return; // Throttling for animation to finish

    const img = document.getElementById('modal-image-img');
    const direction = e.deltaY > 0 ? 1 : -1;

    // Start Exit Animation
    img.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    img.style.opacity = '0';
    img.style.transform = `translateX(${-direction * 50}px) scale(0.95)`;

    setTimeout(() => {
        if (direction > 0) window.playNext?.();
        else window.playPrev?.();

        // Start Enter Animation (Reset position)
        img.style.transition = 'none';
        img.style.transform = `translateX(${direction * 50}px) scale(0.95)`;

        // Trigger reflow
        img.offsetHeight;

        // Animate in
        img.style.transition = 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
        img.style.opacity = '1';
        img.style.transform = 'translateX(0) scale(1)';
    }, 300);

    lastWheelTime = now;
}

window.closeVideoModal = closeVideoModal;
window.closeImageModal = closeImageModal;
window.playVideoFromIndex = (idx) => {
    openMediaAtIndex(idx);
};
window.playStreamFromIndex = (event, idx) => {
    event.stopPropagation();
    window.playVideoFromIndex(idx);
};


